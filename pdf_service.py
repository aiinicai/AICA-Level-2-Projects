"""Page-aware PDF extraction with selective OCR for mixed and scanned PDFs."""
from dataclasses import dataclass
from io import BytesIO
from typing import Callable
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from services.ocr_service import ocr_page
from utils.helpers import normalize_text
from utils.validators import AppError, MAX_PAGES, MAX_TEXT_CHARS, validate_pdf


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    page_count: int
    character_count: int
    status: str
    ocr_pages: tuple[int, ...]
    warnings: tuple[str, ...]


def meaningful(text: str) -> bool:
    letters = sum(ch.isalnum() for ch in text)
    return letters >= 60 and letters / max(len(text), 1) > 0.25


def extract_text_from_pdf(
    data: bytes, filename: str = "notice.pdf", mime_type: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> ExtractionResult:
    validate_pdf(data, filename, mime_type)
    pages: list[str] = []
    scanned: list[int] = []
    warnings: list[str] = []
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if pdf.doc.encryption:
                raise AppError("This PDF is encrypted. Upload an unlocked copy exported by an authorised user.")
            if not pdf.pages:
                raise AppError("This PDF has no pages. Please choose another file.")
            if len(pdf.pages) > MAX_PAGES:
                raise AppError(f"This notice exceeds the {MAX_PAGES}-page limit. Please prepare a smaller complete notice for review.")
            total = 0
            for index, page in enumerate(pdf.pages):
                if progress:
                    progress(f"Reading page {index + 1} of {len(pdf.pages)}…")
                text = normalize_text(page.extract_text() or "")
                if not meaningful(text):
                    text = normalize_text(ocr_page(data, index))
                    scanned.append(index + 1)
                    if not meaningful(text):
                        warnings.append(f"Page {index + 1} contains little readable text. Verify this page in the original PDF.")
                pages.append(f"--- Page {index + 1} ---\n{text}")
                total += len(text)
                if total > MAX_TEXT_CHARS:
                    raise AppError("This PDF contains too much text for one analysis. No pages have been silently omitted; prepare a smaller complete notice.")
                page.close()
    except AppError:
        raise
    except PDFPasswordIncorrect:
        raise AppError("This PDF is password-protected. Please upload an unlocked copy.") from None
    except Exception:
        raise AppError("Unable to read PDF. The document may be encrypted, damaged or too low-resolution.") from None
    combined = "\n\n".join(pages)
    if total < 60:
        raise AppError("We could not reliably read this notice. Please upload a clearer PDF.")
    return ExtractionResult(combined, len(pages), total, "ocr" if scanned else "text", tuple(scanned), tuple(warnings))
