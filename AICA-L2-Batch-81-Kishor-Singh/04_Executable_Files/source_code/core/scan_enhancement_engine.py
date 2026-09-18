"""Scan enhancement: deskew, orientation correction, denoise, and border trimming.

Deliberately dependency-light (no OpenCV) to keep the packaged .exe small:
orientation detection reuses Tesseract's OSD (already a dependency for OCR),
skew estimation uses a simple projection-profile search (numpy only), and
denoise/border-trim use Pillow. None of this is a substitute for a proper
scanner driver's own processing -- it is a best-effort cleanup pass on
already-scanned images, useful mainly to improve OCR accuracy and visual
legibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageFilter

from core.pdf_engine import open_pdf
from core.ocr_engine import configure_pytesseract, find_tesseract


@dataclass
class EnhancementOptions:
    fix_orientation: bool = True
    deskew: bool = True
    denoise: bool = True
    trim_borders: bool = True
    max_deskew_angle: float = 10.0  # degrees; beyond this, assume detection is unreliable and skip
    dpi: int = 300


@dataclass
class PageEnhancementReport:
    page_number: int  # 1-based
    rotation_applied: int = 0  # 0/90/180/270 from orientation detection
    deskew_angle_applied: float = 0.0
    borders_trimmed: bool = False


def detect_orientation(image: Image.Image, tesseract_path: str = "") -> int:
    """Returns the rotation (degrees, one of 0/90/180/270) needed to make text upright.

    Returns 0 (no rotation) if Tesseract is unavailable or OSD is inconclusive
    -- this is a best-effort enhancement, never a hard requirement.
    """
    if not find_tesseract(tesseract_path):
        return 0
    try:
        pytesseract = configure_pytesseract(tesseract_path)
        osd = pytesseract.image_to_osd(image)
        for line in osd.splitlines():
            if line.startswith("Rotate:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:  # noqa: BLE001 - OSD fails on near-blank/very noisy pages; just skip
        pass
    return 0


def estimate_skew_angle(image: Image.Image, max_angle: float = 10.0, step: float = 0.5) -> float:
    """Estimate the small (< max_angle degree) skew of a scanned page via a
    projection-profile search: the correctly-deskewed angle maximises the
    variance of row-wise dark-pixel counts (text lines become sharp horizontal
    bands rather than a smear). Pure numpy/Pillow, no OpenCV dependency."""
    gray = image.convert("L")
    # Downscale for speed -- skew estimation doesn't need full resolution.
    gray.thumbnail((800, 800))
    arr = np.array(gray)
    dark = arr < 128  # boolean mask of "ink" pixels, works for typical dark-text-on-light-background scans

    best_angle = 0.0
    best_score = -1.0
    angle = -max_angle
    while angle <= max_angle:
        rotated = Image.fromarray(dark).rotate(angle, expand=False, fillcolor=0)
        row_sums = np.array(rotated).sum(axis=1)
        score = float(np.var(row_sums))
        if score > best_score:
            best_score = score
            best_angle = angle
        angle += step
    return best_angle


def trim_borders(image: Image.Image, tolerance: int = 12, padding_px: int = 15) -> Image.Image:
    """Crop uniform light-colored scanner borders/margins, keeping actual content."""
    gray = np.array(image.convert("L"))
    content_mask = gray < (255 - tolerance)
    if not content_mask.any():
        return image
    rows = content_mask.any(axis=1)
    cols = content_mask.any(axis=0)
    top, bottom = int(rows.argmax()), int(len(rows) - rows[::-1].argmax())
    left, right = int(cols.argmax()), int(len(cols) - cols[::-1].argmax())
    top = max(0, top - padding_px)
    left = max(0, left - padding_px)
    bottom = min(image.height, bottom + padding_px)
    right = min(image.width, right + padding_px)
    return image.crop((left, top, right, bottom))


def denoise(image: Image.Image) -> Image.Image:
    """Light median-filter denoise -- removes scanner speckle without blurring text much."""
    return image.filter(ImageFilter.MedianFilter(size=3))


def enhance_pdf(
    source_path: str | Path, output_path: str | Path, options: EnhancementOptions, tesseract_path: str = ""
) -> list[PageEnhancementReport]:
    """Apply the requested enhancement steps to every page, saved as a new PDF.

    Each page is re-rasterized at ``options.dpi`` and replaces the original
    page content -- appropriate for scanned pages that are already just an
    image. Do not run this on digitally-created (vector text) PDFs, since it
    will rasterize their text.
    """
    reports: list[PageEnhancementReport] = []
    with open_pdf(source_path) as doc:
        out_doc = fitz.open()
        for page_index in range(doc.page_count):
            page = doc[page_index]
            zoom = options.dpi / 72.0
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

            report = PageEnhancementReport(page_number=page_index + 1)

            if options.fix_orientation:
                rotation = detect_orientation(image, tesseract_path)
                if rotation:
                    image = image.rotate(-rotation, expand=True)
                    report.rotation_applied = rotation

            if options.deskew:
                angle = estimate_skew_angle(image, max_angle=options.max_deskew_angle)
                if abs(angle) > 0.1:
                    image = image.rotate(angle, expand=True, fillcolor=(255, 255, 255))
                    report.deskew_angle_applied = angle

            if options.denoise:
                image = denoise(image)

            if options.trim_borders:
                trimmed = trim_borders(image)
                if trimmed.size != image.size:
                    image = trimmed
                    report.borders_trimmed = True

            reports.append(report)

            new_page = out_doc.new_page(width=image.width * 72.0 / options.dpi, height=image.height * 72.0 / options.dpi)
            import io

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            new_page.insert_image(new_page.rect, stream=buf.getvalue())

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_doc.save(str(output_path), garbage=3, deflate=True)
        out_doc.close()

    return reports
