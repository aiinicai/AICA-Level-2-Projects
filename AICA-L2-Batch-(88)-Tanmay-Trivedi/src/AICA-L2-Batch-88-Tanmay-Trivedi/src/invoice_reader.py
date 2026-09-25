"""
invoice_reader.py
-------------------
Reads an uploaded invoice (photo or PDF) and returns a plain-text description
of the goods/services shown on it, suitable for feeding into the same
Section 17(5) matcher used by Quick Check and Bulk Check (src/rules.py).

Two ways to read the invoice, tried in this order:

  1. AI reading (Claude, vision/document input) - only if ANTHROPIC_API_KEY is
     set. Generally more accurate on real-world invoice layouts (tables,
     stamps, mixed fonts), and works directly off a photo or a PDF without a
     separate OCR engine.
  2. Free/offline fallback - used when no key is set, or if the AI call
     fails for any reason:
       - For a PDF with a real text layer (not scanned), the text is read
         directly (via PyMuPDF) - fast and perfectly accurate.
       - Otherwise (a scanned PDF, or a photo/image file), the page/image is
         OCR'd with Tesseract (via pytesseract). This needs the Tesseract
         OCR engine installed on the machine - pytesseract is only a thin
         Python wrapper around it, not an OCR engine by itself. See the
         README for install instructions per OS. On Windows, if the engine
         isn't on PATH, this module also checks the installer's own default
         location (`C:\Program Files\Tesseract-OCR\tesseract.exe`) before
         giving up - see `_configure_tesseract()` below.

Either way, this module's ONLY job is to turn the uploaded file into text.
Matching that text against Section 17(5) and reaching a verdict is still
done entirely by src/rules.py - exactly the same engine Quick Check and
Bulk Check use - so the legal logic stays defined in exactly one place.

Privacy: nothing here is written to disk. When the AI path is used, the
invoice's actual image/PDF bytes are sent to Anthropic's API for that one
reading request (that is unavoidable - reading a photo needs a vision
model to see it). The OCR fallback is entirely offline; nothing leaves the
machine.
"""

from __future__ import annotations

import base64
import io
import os
import shutil
from dataclasses import dataclass

AI = "ai"
PDF_TEXT = "pdf-text"
OCR = "ocr"

MIN_PDF_TEXT_CHARS = 40  # below this, treat the PDF as scanned/image-only rather than text-based


@dataclass
class ReadResult:
    text: str
    method: str | None  # one of AI / PDF_TEXT / OCR, or None if nothing could be read
    error: str | None = None


METHOD_LABELS = {
    AI: "Claude (AI reading)",
    PDF_TEXT: "PDF text layer (no OCR needed)",
    OCR: "Tesseract OCR (offline)",
}


def _is_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


def _ai_read(file_bytes: bytes, filename: str, is_pdf: bool) -> str | None:
    """Ask Claude to read the invoice directly. Returns None (never raises)
    if there's no API key, the `anthropic` package isn't installed, or the
    call fails for any reason - the caller then falls back to OCR."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

        if is_pdf:
            content_block = {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            }
        else:
            lower = filename.lower()
            if lower.endswith(".png"):
                media_type = "image/png"
            elif lower.endswith(".webp"):
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"
            content_block = {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": b64},
            }

        prompt = (
            "This is a purchase invoice. In plain English, describe the goods or services "
            "supplied, the way a chartered accountant would record it in an expense ledger line "
            "(for example: 'Motor car insurance premium', 'Outdoor catering services for a "
            "corporate event', 'Cement and TMT bars for building construction'). If there are "
            "several clearly different line items, list each briefly on its own line. Do not "
            "include amounts, GSTIN, invoice number or vendor name - only the nature of what was "
            "supplied, described plainly enough for a keyword-based rules engine to recognise the "
            "type of expense."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": [content_block, {"type": "text", "text": prompt}]}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text")).strip()
        return text or None
    except Exception:
        return None


def _pdf_text_layer(file_bytes: bytes) -> str:
    import pymupdf

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc).strip()
    finally:
        doc.close()


def _pdf_first_page_to_png(file_bytes: bytes) -> bytes:
    import pymupdf

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    try:
        pix = doc[0].get_pixmap(dpi=200)
        return pix.tobytes("png")
    finally:
        doc.close()


_TESSERACT_CONFIGURED = False


def _configure_tesseract(pytesseract_module) -> None:
    """pytesseract needs to know where the Tesseract *engine* binary is - on
    Windows this is very commonly installed without ending up on PATH, even
    when the installer's "Add to PATH" box was ticked (it only takes effect
    in a NEW terminal). Rather than make every user edit PATH and restart
    their terminal, try the installer's default locations first - only runs
    once, and only if the engine isn't already resolvable as-is."""
    global _TESSERACT_CONFIGURED
    if _TESSERACT_CONFIGURED:
        return
    _TESSERACT_CONFIGURED = True

    override = os.environ.get("TESSERACT_CMD")
    if override and os.path.isfile(override):
        pytesseract_module.pytesseract.tesseract_cmd = override
        return

    current = pytesseract_module.pytesseract.tesseract_cmd or "tesseract"
    if shutil.which(current):
        return  # already resolvable - leave it alone

    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.isfile(candidate):
            pytesseract_module.pytesseract.tesseract_cmd = candidate
            return


def _ocr_read(file_bytes: bytes, is_pdf: bool) -> str:
    import pytesseract
    from PIL import Image

    _configure_tesseract(pytesseract)

    if is_pdf:
        img = Image.open(io.BytesIO(_pdf_first_page_to_png(file_bytes)))
    else:
        img = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(img).strip()


def read_invoice(file_bytes: bytes, filename: str) -> ReadResult:
    """Best-effort read of an uploaded invoice. Tries AI first (if a key is
    configured), then a free/offline fallback. Never raises - always
    returns a ReadResult, with `.error` set only if nothing could be read
    at all."""
    is_pdf = _is_pdf(filename)

    ai_text = _ai_read(file_bytes, filename, is_pdf)
    if ai_text:
        return ReadResult(text=ai_text, method=AI)

    if is_pdf:
        try:
            layer_text = _pdf_text_layer(file_bytes)
        except Exception:
            layer_text = ""
        if len(layer_text) >= MIN_PDF_TEXT_CHARS:
            return ReadResult(text=layer_text, method=PDF_TEXT)

    try:
        ocr_text = _ocr_read(file_bytes, is_pdf)
    except Exception as exc:
        return ReadResult(
            text="",
            method=None,
            error=(
                "Could not read this file offline. The free OCR fallback needs the Tesseract OCR "
                "engine installed on this machine (pytesseract only wraps it - it isn't an OCR "
                "engine by itself). See the README for install steps, or set ANTHROPIC_API_KEY to "
                f"use AI reading instead. (Details: {exc})"
            ),
        )

    if not ocr_text.strip():
        return ReadResult(
            text="",
            method=None,
            error=(
                "No readable text was found in this file. Try a clearer photo/scan, or describe "
                "the expense manually in Quick Check instead."
            ),
        )
    return ReadResult(text=ocr_text, method=OCR)
