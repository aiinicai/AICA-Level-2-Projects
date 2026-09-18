"""Tests for core.split_engine."""
import pytest

from core.pdf_engine import open_pdf
from core.split_engine import SplitEngine
from utils.validation import ValidationError


def test_split_every_page(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 5)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).split_every_page()
    assert result.total_output_files == 5
    for f in result.output_files:
        assert f.page_count == 1


def test_split_by_ranges(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 20)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).split_by_ranges(["1-5", "6-10", "11-20"])
    assert result.total_output_files == 3
    assert [f.page_count for f in result.output_files] == [5, 5, 10]


def test_extract_pages(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 10)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).extract_pages("1,3,7-10")
    assert result.total_output_files == 1
    assert result.output_files[0].page_count == 6  # 1,3,7,8,9,10


def test_split_every_n_pages(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 11)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).split_every_n_pages(5)
    assert [f.page_count for f in result.output_files] == [5, 5, 1]


def test_split_into_equal_parts(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 100)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).split_into_equal_parts(5)
    assert result.total_output_files == 5
    assert sum(f.page_count for f in result.output_files) == 100
    assert all(f.page_count == 20 for f in result.output_files)


def test_split_into_equal_parts_uneven(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 10)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).split_into_equal_parts(3)
    sizes = sorted(f.page_count for f in result.output_files)
    assert sizes == [3, 3, 4]
    assert sum(sizes) == 10


def test_split_equal_parts_more_than_pages_raises(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 3)
    with pytest.raises(ValidationError):
        SplitEngine(src, output_folder=tmp_path / "out").split_into_equal_parts(10)


def test_remove_pages(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 10)
    out_dir = tmp_path / "out"
    result = SplitEngine(src, output_folder=out_dir).remove_pages("2,5,8")
    assert result.output_files[0].page_count == 7
    assert result.output_files[0].source_pages == [1, 3, 4, 6, 7, 9, 10]


def test_remove_all_pages_raises(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 2)
    with pytest.raises(ValidationError):
        SplitEngine(src, output_folder=tmp_path / "out").remove_pages("all")


def test_split_source_untouched(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 5)
    original = src.read_bytes()
    SplitEngine(src, output_folder=tmp_path / "out").split_every_page()
    assert src.read_bytes() == original


def test_single_page_pdf_split_every_page(make_pdf, tmp_path):
    src = make_pdf("single.pdf", 1)
    result = SplitEngine(src, output_folder=tmp_path / "out").split_every_page()
    assert result.total_output_files == 1
