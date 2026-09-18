"""Tests for core.scan_enhancement_engine: deskew, border trim, denoise.

Orientation-detection tests are skipped without Tesseract (OSD needs it);
deskew, border-trim and denoise are pure numpy/Pillow and always run.
"""
from __future__ import annotations

import fitz
import numpy as np
import pytest
from PIL import Image

from core.ocr_engine import is_tesseract_available
from core.scan_enhancement_engine import (
    EnhancementOptions,
    denoise,
    detect_orientation,
    enhance_pdf,
    estimate_skew_angle,
    trim_borders,
)


def _bordered_image(inner_size=(600, 800), border=150, fill_pattern=True) -> Image.Image:
    canvas = Image.new("L", (inner_size[0] + 2 * border, inner_size[1] + 2 * border), 255)
    inner = Image.new("L", inner_size, 255)
    if fill_pattern:
        arr = np.array(inner)
        arr[::20, :] = 0  # a few horizontal dark lines simulating text rows
        inner = Image.fromarray(arr)
    canvas.paste(inner, (border, border))
    return canvas.convert("RGB")


def test_estimate_skew_angle_detects_known_rotation():
    image = _bordered_image()
    rotated = image.rotate(5, expand=True, fillcolor=(255, 255, 255))
    angle = estimate_skew_angle(rotated, max_angle=10.0, step=0.5)
    # The correcting angle should be close to -5 (undo the +5 degree skew).
    assert -6.0 <= angle <= -4.0


def test_estimate_skew_angle_near_zero_for_unrotated_image():
    image = _bordered_image()
    angle = estimate_skew_angle(image, max_angle=10.0, step=0.5)
    assert abs(angle) <= 1.0


def test_trim_borders_removes_uniform_margin():
    image = _bordered_image(inner_size=(400, 500), border=200)
    trimmed = trim_borders(image, padding_px=5)
    assert trimmed.width < image.width
    assert trimmed.height < image.height
    # Content dimensions should be roughly preserved (within the padding, plus
    # a little slack since the synthetic stripe pattern's last line doesn't
    # land exactly on the final row).
    assert 390 <= trimmed.width <= 430
    assert 480 <= trimmed.height <= 530


def test_trim_borders_noop_on_fully_blank_image():
    blank = Image.new("RGB", (300, 300), "white")
    result = trim_borders(blank)
    assert result.size == blank.size  # nothing to trim -- returned unchanged


def test_denoise_reduces_speckle_pixel_count():
    arr = np.full((200, 200), 255, dtype="uint8")
    rng = np.random.default_rng(3)
    speckle = rng.random(arr.shape) < 0.05
    arr[speckle] = 0
    speckled = Image.fromarray(arr)
    cleaned = denoise(speckled)
    original_dark = int((np.array(speckled) < 128).sum())
    cleaned_dark = int((np.array(cleaned) < 128).sum())
    assert cleaned_dark < original_dark


def test_detect_orientation_without_tesseract_returns_zero(monkeypatch):
    monkeypatch.setattr("core.scan_enhancement_engine.find_tesseract", lambda path="": None)
    image = _bordered_image()
    assert detect_orientation(image) == 0


@pytest.mark.skipif(not is_tesseract_available(), reason="Tesseract not installed")
def test_enhance_pdf_end_to_end(tmp_path):
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (1200, 1600), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    for i in range(4):
        d.text((100, 150 + i * 70), f"Line {i + 1} of the document.", fill="black", font=font)

    bordered = Image.new("RGB", (1600, 2000), "white")
    bordered.paste(img, (150, 150))
    skewed = bordered.rotate(3, expand=True, fillcolor=(255, 255, 255))

    img_path = tmp_path / "scan.png"
    skewed.save(img_path)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), filename=str(img_path))
    src = tmp_path / "scan.pdf"
    doc.save(str(src))
    doc.close()

    out = tmp_path / "enhanced.pdf"
    reports = enhance_pdf(src, out, EnhancementOptions())

    assert len(reports) == 1
    assert reports[0].borders_trimmed
    assert abs(reports[0].deskew_angle_applied) > 0.5

    with fitz.open(str(out)) as d2:
        assert d2.page_count == 1
        pixmap = d2[0].get_pixmap()
        assert pixmap.width > 0


def test_original_file_untouched(tmp_path):
    image = _bordered_image()
    img_path = tmp_path / "scan.png"
    image.save(img_path)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), filename=str(img_path))
    src = tmp_path / "scan.pdf"
    doc.save(str(src))
    doc.close()
    original_bytes = src.read_bytes()

    enhance_pdf(src, tmp_path / "out.pdf", EnhancementOptions())
    assert src.read_bytes() == original_bytes
