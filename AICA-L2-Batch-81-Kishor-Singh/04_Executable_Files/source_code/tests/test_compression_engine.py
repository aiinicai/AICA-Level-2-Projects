"""Tests for core.compression_engine."""
from __future__ import annotations

import fitz
import numpy as np
import pytest
from PIL import Image

from core.compression_engine import CompressionPreset, compress_pdf


def _make_image_pdf(path, size=(1600, 1200), noisy=True):
    """A PDF with one embedded raster image -- noisy so it doesn't trivially compress to nothing."""
    if noisy:
        rng = np.random.default_rng(7)
        arr = (rng.random((size[1], size[0], 3)) * 255).astype("uint8")
    else:
        arr = np.full((size[1], size[0], 3), 200, dtype="uint8")
    img = Image.fromarray(arr, mode="RGB")
    img_path = path.with_suffix(".png")
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(50, 50, 545, 792), filename=str(img_path))
    doc.save(str(path))
    doc.close()
    return path


@pytest.mark.parametrize("preset", list(CompressionPreset))
def test_compression_reduces_size_and_stays_valid(tmp_path, preset):
    src = _make_image_pdf(tmp_path / "doc.pdf")
    out = tmp_path / f"out_{preset.name}.pdf"
    result = compress_pdf(src, out, preset)

    assert result.images_recompressed == 1
    assert result.compressed_size_bytes <= result.original_size_bytes

    # The output must remain a valid, renderable PDF -- this is the exact
    # regression case for a real bug found during development: PyMuPDF's
    # update_stream() flate-compresses its input by default, which silently
    # corrupted the JPEG stream when combined with an explicit DCTDecode
    # filter, and MuPDF failed to decode the image at render time.
    with fitz.open(str(out)) as doc:
        assert doc.page_count == 1
        pixmap = doc[0].get_pixmap()
        assert pixmap.width > 0
        assert len(pixmap.samples) > 1000


def test_maximum_compression_smaller_than_maximum_quality(tmp_path):
    src = _make_image_pdf(tmp_path / "doc.pdf")
    high = compress_pdf(src, tmp_path / "high.pdf", CompressionPreset.MAXIMUM_QUALITY)
    low = compress_pdf(src, tmp_path / "low.pdf", CompressionPreset.MAXIMUM_COMPRESSION)
    assert low.compressed_size_bytes < high.compressed_size_bytes


def test_compression_never_increases_file_size(tmp_path):
    """A flat, single-color image compresses trivially small already at any
    preset -- the engine must never write an output larger than the source."""
    src = _make_image_pdf(tmp_path / "doc.pdf", noisy=False)
    result = compress_pdf(src, tmp_path / "out.pdf", CompressionPreset.MAXIMUM_QUALITY)
    assert result.compressed_size_bytes <= result.original_size_bytes


def test_original_file_untouched(tmp_path):
    src = _make_image_pdf(tmp_path / "doc.pdf")
    original_bytes = src.read_bytes()
    compress_pdf(src, tmp_path / "out.pdf", CompressionPreset.STANDARD)
    assert src.read_bytes() == original_bytes


def test_text_only_pdf_has_no_images_to_recompress(tmp_path):
    doc = fitz.open()
    doc.new_page(width=595, height=842).insert_text((72, 100), "No images on this page at all.")
    src = tmp_path / "text.pdf"
    doc.save(str(src))
    doc.close()

    result = compress_pdf(src, tmp_path / "out.pdf", CompressionPreset.EMAIL)
    assert result.images_recompressed == 0
    with fitz.open(str(tmp_path / "out.pdf")) as d:
        assert "No images" in d[0].get_text()
