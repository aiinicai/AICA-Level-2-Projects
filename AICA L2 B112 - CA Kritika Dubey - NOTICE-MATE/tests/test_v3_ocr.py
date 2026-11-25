"""V3 — OCR reliability: health check, blank/partial detection, parse gating."""
import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from noticemate.services import extraction
from noticemate.services.extraction import extract, ocr_health

from .conftest import sample


def _blank_pdf() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (1240, 1754), "white").save(b, "PDF")
    return b.getvalue()


def _mixed_pdf() -> bytes:
    """Page 1 = scanned text image, page 2 = blank scan."""
    p1 = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(p1)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 40)
    except Exception:
        f = ImageFont.load_default()
    for i, line in enumerate(["FICTIONAL TEST NOTICE", "Section 143(2) Assessment Year 2026-27", "Please explain cash deposits"]):
        d.text((100, 200 + 80 * i), line, fill="black", font=f)
    p2 = Image.new("RGB", (1240, 1754), "white")
    b = io.BytesIO()
    p1.save(b, "PDF", save_all=True, append_images=[p2])
    return b.getvalue()


def test_health_ready_here():
    h = ocr_health()
    assert h["status"] == "READY", h
    assert h["self_test"]["ok"]


def test_scanned_notice_reads():
    ex = extract(".pdf", sample("notice_143_2_PQR_scanned.pdf"))
    assert ex.status == "OCR" and len(ex.text.strip()) > 1000
    assert ex.pages[0]["method"] == "OCR" and ex.pages[0]["status"] in ("OK", "LOW_CONFIDENCE")


def test_blank_scan_is_failed_not_ok():
    ex = extract(".pdf", _blank_pdf())
    assert ex.status == "FAILED"
    assert any("NO TEXT WAS EXTRACTED" in n for n in ex.notes)


def test_mixed_pages_partial():
    ex = extract(".pdf", _mixed_pdf())
    assert ex.status == "PARTIAL"
    assert [p["status"] for p in ex.pages][1] == "BLANK"
    assert any("PARTIAL EXTRACTION" in n for n in ex.notes)


def test_bad_poppler_path(monkeypatch):
    monkeypatch.setenv("POPPLER_PATH", "/does/not/exist")
    h = ocr_health()
    assert h["status"] == "DEGRADED" and "POPPLER_PATH" in h["poppler"]["error"]
    ex = extract(".pdf", sample("notice_143_2_PQR_scanned.pdf"))
    assert ex.status == "FAILED"
    assert any("Poppler" in n for n in ex.notes)


def test_bad_tesseract_path(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", "/does/not/exist/tesseract.exe")
    h = ocr_health()
    assert h["status"] == "UNAVAILABLE"
    ex = extract(".pdf", sample("notice_143_2_PQR_scanned.pdf"))
    assert ex.status == "FAILED"
    monkeypatch.delenv("TESSERACT_CMD")
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = "tesseract"


def test_parse_gate_blocks_failed_and_requires_ack_for_partial(users):
    from noticemate.core.errors import ValidationError
    from noticemate.services import cases, documents, notices

    staff = users["staff"]
    c = cases.create_case(staff, case_ref="OCR-GATE", assessee_name="Fictional OCR Co", pan="AAAFO1234Z",
                          assessee_category="FIRM", assessment_year="2026-27")
    d1 = documents.upload(staff, c["id"], "blank.pdf", _blank_pdf())
    assert d1["extraction_status"] == "FAILED"
    with pytest.raises(ValidationError):
        notices.create_from_document(staff, d1["id"])
    d2 = documents.upload(staff, c["id"], "mixed.pdf", _mixed_pdf())
    assert d2["extraction_status"] == "PARTIAL"
    assert d2["extraction_pages_json"][1]["status"] == "BLANK"
    with pytest.raises(ValidationError) as e:
        notices.create_from_document(staff, d2["id"])
    assert e.value.details.get("needs_acknowledgement")
    n = notices.create_from_document(staff, d2["id"], acknowledge_partial=True)
    assert n["id"]
