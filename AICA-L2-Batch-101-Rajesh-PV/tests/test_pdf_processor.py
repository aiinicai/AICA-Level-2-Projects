import threading

import pytest

from judgment_analyzer.pdf_processor import (CancelledError, PDFError, clean_text, extract_text,
                                             format_file_size, tesseract_available, text_layer_ratio,
                                             validate_pdf, _compress_ranges)


def test_validate_text_pdf_reports_info(text_pdf):
    info = validate_pdf(text_pdf)
    assert info.file_name == "sample_judgment.pdf"
    assert info.page_count == 3
    assert info.file_size_bytes > 0
    assert info.file_size_display.endswith(("KB", "bytes"))


@pytest.mark.parametrize("name,content,expected", [
    ("notes.txt", b"hello", "Unsupported file type"),
    ("empty.pdf", b"", "empty"),
    ("fake.pdf", b"This is not a PDF at all", "missing PDF header"),
    ("broken.pdf", b"%PDF-1.7\n garbage garbage", "could not be opened"),
])
def test_validate_rejects_bad_files(tmp_path, name, content, expected):
    path = tmp_path / name
    path.write_bytes(content)
    with pytest.raises(PDFError, match=expected):
        validate_pdf(path)


def test_validate_missing_file(tmp_path):
    with pytest.raises(PDFError, match="could not be found"):
        validate_pdf(tmp_path / "nope.pdf")


def test_validate_rejects_oversized(text_pdf):
    with pytest.raises(PDFError, match="larger than"):
        validate_pdf(text_pdf, max_size_mb=0.000001)


def test_validate_rejects_password_protected(encrypted_pdf):
    with pytest.raises(PDFError, match="password"):
        validate_pdf(encrypted_pdf)


def test_extract_text_pdf_with_page_markers(text_pdf):
    doc = extract_text(validate_pdf(text_pdf), ocr_mode="Off")
    assert len(doc.pages) == 3
    assert doc.ocr_page_count == 0
    full = doc.full_text()
    assert "[Page 1]" in full and "[Page 3]" in full
    assert "Civil Appeal No. 123 of 2024" in full
    assert "appeal is allowed" in full


def test_extract_reports_progress(text_pdf):
    calls = []
    extract_text(validate_pdf(text_pdf), ocr_mode="Off", progress=lambda d, t, m: calls.append((d, t)))
    assert calls[-1] == (3, 3)


def test_extract_can_be_cancelled(text_pdf):
    event = threading.Event()
    event.set()
    with pytest.raises(CancelledError):
        extract_text(validate_pdf(text_pdf), cancel_event=event)


def test_scanned_pdf_detected(scanned_pdf):
    assert text_layer_ratio(validate_pdf(scanned_pdf)) == 0.0


def test_scanned_pdf_without_ocr_raises(scanned_pdf):
    with pytest.raises(PDFError):
        extract_text(validate_pdf(scanned_pdf), ocr_mode="Off")


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract OCR not installed")
def test_scanned_pdf_ocr(scanned_pdf):
    doc = extract_text(validate_pdf(scanned_pdf), ocr_mode="Auto")
    assert doc.ocr_page_count == 1
    assert "dismissed" in doc.full_text().lower()
    assert any("OCR was used" in w for w in doc.warnings)


def test_text_pdf_ratio(text_pdf):
    assert text_layer_ratio(validate_pdf(text_pdf)) == 1.0


def test_clean_text_normalises_whitespace():
    assert clean_text("a   b\r\n\r\n\r\n\nc­ d\x00") == "a b\n\nc d"


def test_helpers():
    assert format_file_size(512) == "512 bytes"
    assert format_file_size(2048) == "2.0 KB"
    assert _compress_ranges([1, 2, 3, 7, 9, 10]) == "1-3, 7, 9-10"
