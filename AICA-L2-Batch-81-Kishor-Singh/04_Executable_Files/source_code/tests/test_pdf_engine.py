"""Tests for core.pdf_engine: opening, page info, encryption handling."""
import fitz
import pytest

from core.pdf_engine import get_page_count, get_page_info, is_encrypted, open_pdf, validate_pdf_integrity
from tests.conftest import A4
from utils.validation import EncryptedPdfError, ValidationError


def test_open_pdf_and_page_count(make_pdf):
    p = make_pdf("simple.pdf", 5)
    assert get_page_count(p) == 5


def test_single_page_pdf(make_pdf):
    p = make_pdf("single.pdf", 1)
    assert get_page_count(p) == 1


def test_hundred_page_pdf(make_pdf):
    p = make_pdf("big.pdf", 100)
    assert get_page_count(p) == 100


def test_portrait_a4_page_size(make_pdf):
    p = make_pdf("portrait.pdf", 1, size=A4, landscape=False)
    with open_pdf(p) as doc:
        info = get_page_info(doc, 0)
    assert info.width_pt == 595
    assert info.height_pt == 842
    assert not info.is_landscape


def test_landscape_a4_page_size(make_pdf):
    p = make_pdf("landscape.pdf", 1, size=A4, landscape=True)
    with open_pdf(p) as doc:
        info = get_page_info(doc, 0)
    assert info.width_pt == 842
    assert info.height_pt == 595
    assert info.is_landscape


def test_legal_page_size(make_pdf):
    from tests.conftest import LEGAL

    p = make_pdf("legal.pdf", 1, size=LEGAL)
    with open_pdf(p) as doc:
        info = get_page_info(doc, 0)
    assert (info.width_pt, info.height_pt) == LEGAL


def test_mixed_size_document(tmp_path):
    doc = fitz.open()
    doc.new_page(width=595, height=842)  # A4 portrait
    doc.new_page(width=612, height=1008)  # Legal
    doc.new_page(width=842, height=595)  # A4 landscape
    path = tmp_path / "mixed.pdf"
    doc.save(str(path))
    doc.close()

    with open_pdf(path) as reopened:
        sizes = [(get_page_info(reopened, i).width_pt, get_page_info(reopened, i).height_pt) for i in range(3)]
    assert sizes == [(595, 842), (612, 1008), (842, 595)]


def test_missing_file_raises():
    with pytest.raises(ValidationError):
        open_pdf("Z:/does/not/exist.pdf")


def test_encrypted_pdf_without_password_raises(encrypted_pdf):
    assert is_encrypted(encrypted_pdf)
    with pytest.raises(EncryptedPdfError):
        open_pdf(encrypted_pdf)


def test_encrypted_pdf_with_wrong_password_raises(encrypted_pdf):
    with pytest.raises(EncryptedPdfError):
        open_pdf(encrypted_pdf, password="wrong-password")


def test_encrypted_pdf_with_correct_password_opens(encrypted_pdf):
    with open_pdf(encrypted_pdf, password="user-secret") as doc:
        assert doc.page_count == 1


def test_permission_restricted_pdf_raises_even_with_correct_password(permission_restricted_pdf):
    # The user password is correct, but the owner has disallowed modification --
    # the app must refuse to process it rather than bypass that restriction.
    with pytest.raises(ValidationError):
        open_pdf(permission_restricted_pdf, password="user-secret")


def test_validate_pdf_integrity_reports_encrypted(encrypted_pdf):
    ok, reason = validate_pdf_integrity(encrypted_pdf)
    assert ok
    assert "password" in reason.lower()


def test_validate_pdf_integrity_ok(make_pdf):
    p = make_pdf("ok.pdf", 3)
    ok, reason = validate_pdf_integrity(p)
    assert ok
    assert reason == ""


def test_validate_pdf_integrity_corrupt(tmp_path):
    p = tmp_path / "corrupt.pdf"
    p.write_bytes(b"not a real pdf file")
    ok, reason = validate_pdf_integrity(p)
    assert not ok


def test_open_pdf_repairs_truncated_file_via_pikepdf(tmp_path):
    """A PDF with a damaged tail (common with truncated downloads/scanner
    output) should be recoverable via the pikepdf/qpdf repair fallback
    rather than being rejected outright as unreadable."""
    path = tmp_path / "truncated.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(str(path))
    doc.close()

    data = path.read_bytes()
    path.write_bytes(data[: len(data) - 40])  # damage the xref/trailer tail

    with open_pdf(path) as doc:
        assert doc.page_count == 1


def test_totally_unparseable_file_still_raises(tmp_path):
    p = tmp_path / "garbage.pdf"
    p.write_bytes(b"this is not a pdf at all, no header, no structure")
    with pytest.raises(ValidationError):
        open_pdf(p)
