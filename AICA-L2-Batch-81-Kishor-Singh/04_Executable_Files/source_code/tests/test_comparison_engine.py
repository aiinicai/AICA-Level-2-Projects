"""Tests for core.comparison_engine."""
from __future__ import annotations

import fitz

from core.comparison_engine import compare_text, render_page_diff_image


def _pdf(path, pages_text: list[str]):
    doc = fitz.open()
    for text in pages_text:
        p = doc.new_page(width=595, height=842)
        p.insert_text((72, 100), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


def test_identical_documents_report_no_changes(tmp_path):
    a = _pdf(tmp_path / "a.pdf", ["Same text on page 1", "Same text on page 2"])
    b = _pdf(tmp_path / "b.pdf", ["Same text on page 1", "Same text on page 2"])
    result = compare_text(a, b)
    assert result.identical
    assert result.pages_with_changes == []


def test_changed_page_is_detected_with_added_removed_lines(tmp_path):
    a = _pdf(tmp_path / "a.pdf", ["Amount: 100000"])
    b = _pdf(tmp_path / "b.pdf", ["Amount: 118000"])
    result = compare_text(a, b)
    assert not result.identical
    assert result.pages_with_changes == [1]
    diff = result.page_diffs[0]
    assert "Amount: 100000" in diff.removed_lines
    assert "Amount: 118000" in diff.added_lines


def test_unchanged_page_among_changed_pages(tmp_path):
    a = _pdf(tmp_path / "a.pdf", ["Page one unchanged", "Old page two"])
    b = _pdf(tmp_path / "b.pdf", ["Page one unchanged", "New page two"])
    result = compare_text(a, b)
    assert result.pages_with_changes == [2]
    assert result.page_diffs[0].unchanged
    assert not result.page_diffs[1].unchanged


def test_extra_pages_in_second_document_reported(tmp_path):
    a = _pdf(tmp_path / "a.pdf", ["Only page"])
    b = _pdf(tmp_path / "b.pdf", ["Only page", "A brand new second page"])
    result = compare_text(a, b)
    assert result.document_a_pages == 1
    assert result.document_b_pages == 2
    assert 2 in result.pages_with_changes


def test_render_page_diff_image_produces_valid_png(tmp_path):
    a = _pdf(tmp_path / "a.pdf", ["Version A content here"])
    b = _pdf(tmp_path / "b.pdf", ["Version B content differs"])
    png_bytes = render_page_diff_image(a, b, 0)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # valid PNG signature
    assert len(png_bytes) > 100
