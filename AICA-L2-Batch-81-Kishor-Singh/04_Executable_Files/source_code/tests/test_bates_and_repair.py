"""Tests for Bates numbering (core.watermark_engine) and standalone PDF repair (core.pdf_engine)."""
from __future__ import annotations

import fitz

from core.pdf_engine import repair_pdf
from core.watermark_engine import BatesNumberingOptions, add_bates_numbering
from models.enums import PositionPreset


def _pdf(path, page_count=3):
    doc = fitz.open()
    for i in range(page_count):
        doc.new_page(width=595, height=842).insert_text((72, 100), f"Page {i + 1}")
    doc.save(str(path))
    doc.close()
    return path


def test_bates_numbering_labels_are_sequential(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 3)
    out = tmp_path / "bates.pdf"
    result = add_bates_numbering(src, out, BatesNumberingOptions(prefix="ABC-", digit_count=6, start_number=1))
    assert result.first_number == 1
    assert result.last_number == 3
    assert result.next_start_number == 4

    with fitz.open(str(out)) as doc:
        assert "ABC-000001" in doc[0].get_text()
        assert "ABC-000002" in doc[1].get_text()
        assert "ABC-000003" in doc[2].get_text()


def test_bates_numbering_continues_across_multiple_files(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 2)
    b = _pdf(tmp_path / "b.pdf", 2)

    result_a = add_bates_numbering(a, tmp_path / "a_bates.pdf", BatesNumberingOptions(prefix="XYZ-", start_number=1))
    result_b = add_bates_numbering(
        b, tmp_path / "b_bates.pdf", BatesNumberingOptions(prefix="XYZ-", start_number=result_a.next_start_number)
    )

    assert result_a.last_number == 2
    assert result_b.first_number == 3
    assert result_b.last_number == 4

    with fitz.open(str(tmp_path / "b_bates.pdf")) as doc:
        assert "XYZ-000003" in doc[0].get_text()
        assert "XYZ-000004" in doc[1].get_text()


def test_bates_numbering_respects_position(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 1)
    out_left = tmp_path / "left.pdf"
    out_right = tmp_path / "right.pdf"
    add_bates_numbering(src, out_left, BatesNumberingOptions(position=PositionPreset.BOTTOM_LEFT))
    add_bates_numbering(src, out_right, BatesNumberingOptions(position=PositionPreset.BOTTOM_RIGHT))
    # Both should produce valid, openable output with the label present.
    for path in (out_left, out_right):
        with fitz.open(str(path)) as doc:
            assert "000001" in doc[0].get_text()


def test_original_file_untouched_by_bates(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 1)
    original = src.read_bytes()
    add_bates_numbering(src, tmp_path / "out.pdf", BatesNumberingOptions())
    assert src.read_bytes() == original


# --------------------------------------------------------------- PDF repair

def test_repair_healthy_pdf_succeeds(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 1)
    result = repair_pdf(src, tmp_path / "out.pdf")
    assert result.page_count == 1
    with fitz.open(str(result.output_path)) as doc:
        assert "Page 1" in doc[0].get_text()


def test_repair_truncated_pdf_recovers_content(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 1)
    data = src.read_bytes()
    src.write_bytes(data[: len(data) - 40])

    result = repair_pdf(src, tmp_path / "out.pdf")
    assert result.repaired
    assert result.page_count == 1
    with fitz.open(str(result.output_path)) as doc:
        assert "Page 1" in doc[0].get_text()


def test_original_file_untouched_by_repair(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 1)
    original = src.read_bytes()
    repair_pdf(src, tmp_path / "out.pdf")
    assert src.read_bytes() == original
