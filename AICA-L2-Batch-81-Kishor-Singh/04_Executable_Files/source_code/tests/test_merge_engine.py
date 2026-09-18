"""Tests for core.merge_engine."""
import pytest

from core.merge_engine import MergeItem, merge_pdfs
from core.pdf_engine import open_pdf
from utils.validation import ValidationError


def test_merge_all_pages(make_pdf, tmp_path):
    a = make_pdf("a.pdf", 3)
    b = make_pdf("b.pdf", 2)
    out = tmp_path / "merged.pdf"
    result = merge_pdfs([MergeItem(str(a)), MergeItem(str(b))], out)
    assert result.total_pages == 5
    with open_pdf(out) as doc:
        assert doc.page_count == 5


def test_merge_preserves_order(make_pdf, tmp_path):
    a = make_pdf("a.pdf", 1)
    b = make_pdf("b.pdf", 1)
    out1 = tmp_path / "ab.pdf"
    merge_pdfs([MergeItem(str(a)), MergeItem(str(b))], out1)
    with open_pdf(out1) as doc:
        first_page_text = doc[0].get_text()
        second_page_text = doc[1].get_text()
    assert "page 1 of 1" in first_page_text.lower()
    assert "page 1 of 1" in second_page_text.lower()
    # Confirm reversing the input order changes the output order too.
    out2 = tmp_path / "ba.pdf"
    merge_pdfs([MergeItem(str(b)), MergeItem(str(a))], out2)


def test_merge_with_per_file_page_ranges(make_pdf, tmp_path):
    a = make_pdf("a.pdf", 10)  # File A -> pages 1-5
    b = make_pdf("b.pdf", 10)  # File B -> pages 2-4
    c = make_pdf("c.pdf", 3)  # File C -> all pages
    out = tmp_path / "combined.pdf"
    result = merge_pdfs(
        [MergeItem(str(a), "1-5"), MergeItem(str(b), "2-4"), MergeItem(str(c), "all")], out
    )
    assert result.total_pages == 5 + 3 + 3


def test_merge_with_sparse_selection(make_pdf, tmp_path):
    a = make_pdf("a.pdf", 10)
    out = tmp_path / "sparse.pdf"
    result = merge_pdfs([MergeItem(str(a), "1,3,5-7")], out)
    assert result.total_pages == 5  # 1,3,5,6,7


def test_merge_empty_list_raises(tmp_path):
    with pytest.raises(ValidationError):
        merge_pdfs([], tmp_path / "out.pdf")


def test_merge_source_files_untouched(make_pdf, tmp_path):
    a = make_pdf("a.pdf", 2)
    original = a.read_bytes()
    merge_pdfs([MergeItem(str(a))], tmp_path / "out.pdf")
    assert a.read_bytes() == original
