"""Tests for core.page_organizer: reorder, delete, rotate, duplicate, insert, extract."""
import pytest

from core.page_organizer import PageOrganizer
from core.pdf_engine import open_pdf
from utils.validation import ValidationError


def test_reorder_pages(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 3)
    with PageOrganizer(src) as organizer:
        organizer.reorder([2, 0, 1])
        out = tmp_path / "reordered.pdf"
        organizer.save_as(out)
    with open_pdf(out) as doc:
        assert "page 3 of 3" in doc[0].get_text().lower()
        assert "page 1 of 3" in doc[1].get_text().lower()
        assert "page 2 of 3" in doc[2].get_text().lower()


def test_delete_pages(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 5)
    with PageOrganizer(src) as organizer:
        organizer.delete_pages([1, 3])  # remove positions 2 and 4 (1-indexed pages)
        out = tmp_path / "deleted.pdf"
        organizer.save_as(out)
    with open_pdf(out) as doc:
        assert doc.page_count == 3


def test_cannot_delete_all_pages(make_pdf):
    src = make_pdf("doc.pdf", 2)
    with PageOrganizer(src) as organizer:
        with pytest.raises(ValidationError):
            organizer.delete_pages([0, 1])


def test_duplicate_page(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 2)
    with PageOrganizer(src) as organizer:
        organizer.duplicate_page(0)
        out = tmp_path / "dup.pdf"
        organizer.save_as(out)
    with open_pdf(out) as doc:
        assert doc.page_count == 3


def test_insert_blank_page(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 2)
    with PageOrganizer(src) as organizer:
        organizer.insert_blank_page(1)
        out = tmp_path / "blank.pdf"
        organizer.save_as(out)
    with open_pdf(out) as doc:
        assert doc.page_count == 3
        assert doc[1].get_text().strip() == ""


def test_insert_other_pdf(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 2)
    other = make_pdf("other.pdf", 3)
    with PageOrganizer(src) as organizer:
        organizer.insert_pdf(1, other, "1-2")
        out = tmp_path / "combined.pdf"
        organizer.save_as(out)
    with open_pdf(out) as doc:
        assert doc.page_count == 4  # 2 original + 2 inserted


def test_extract_pages_subset(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 5)
    with PageOrganizer(src) as organizer:
        out = tmp_path / "extracted.pdf"
        organizer.extract_pages([0, 2, 4], out)
    with open_pdf(out) as doc:
        assert doc.page_count == 3


def test_rotate_page_persists_in_output(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 1)
    with PageOrganizer(src) as organizer:
        organizer.rotate_page(0, 90)
        out = tmp_path / "rotated.pdf"
        organizer.save_as(out)
    with open_pdf(out) as doc:
        assert doc[0].rotation == 90


def test_thumbnails_generated_for_every_page(make_pdf):
    src = make_pdf("doc.pdf", 4)
    with PageOrganizer(src) as organizer:
        thumbs = organizer.get_thumbnails()
    assert len(thumbs) == 4
    assert all(len(t.png_bytes) > 0 for t in thumbs)
