"""Tests for core.ocr_engine. Skipped entirely if Tesseract isn't installed
on the machine running the suite -- these are real OCR calls, not mocks."""
from __future__ import annotations

import fitz
import pytest

from core.ocr_engine import is_tesseract_available, make_searchable_pdf, page_has_extractable_text

pytestmark = pytest.mark.skipif(not is_tesseract_available(), reason="Tesseract OCR is not installed on this machine")


def _make_scanned_page_pdf(path, text_lines: list[str]):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1700, 2200), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
    for i, line in enumerate(text_lines):
        d.text((100, 150 + i * 80), line, fill="black", font=font)
    img_path = path.with_suffix(".png")
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), filename=str(img_path))
    doc.save(str(path))
    doc.close()
    return path


def test_scanned_page_has_no_extractable_text(tmp_path):
    pdf_path = _make_scanned_page_pdf(tmp_path / "scan.pdf", ["Hello World"])
    with fitz.open(str(pdf_path)) as doc:
        assert not page_has_extractable_text(doc, 0)


def test_make_searchable_pdf_recovers_text(tmp_path):
    pdf_path = _make_scanned_page_pdf(tmp_path / "scan.pdf", ["TAX INVOICE", "Total: 118000"])
    out_path = tmp_path / "scan_ocr.pdf"

    result = make_searchable_pdf(pdf_path, out_path)

    assert result.pages_ocred == [1]
    assert result.pages_already_had_text == []
    assert result.average_confidence > 0

    with fitz.open(str(out_path)) as doc:
        text = doc[0].get_text().upper()
        assert "INVOICE" in text
        assert "118000" in text


def test_make_searchable_pdf_skips_pages_with_existing_text(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "This page already has a real text layer, well over the threshold.")
    src = tmp_path / "digital.pdf"
    doc.save(str(src))
    doc.close()

    out_path = tmp_path / "digital_ocr.pdf"
    result = make_searchable_pdf(src, out_path)

    assert result.pages_ocred == []
    assert result.pages_already_had_text == [1]


def test_original_file_untouched_by_ocr(tmp_path):
    pdf_path = _make_scanned_page_pdf(tmp_path / "scan.pdf", ["Original"])
    original_bytes = pdf_path.read_bytes()
    make_searchable_pdf(pdf_path, tmp_path / "out.pdf")
    assert pdf_path.read_bytes() == original_bytes
