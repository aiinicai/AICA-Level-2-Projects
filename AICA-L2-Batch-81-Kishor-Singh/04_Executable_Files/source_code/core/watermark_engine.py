"""Text/image watermarking and page-numbering.

Kept separate from :mod:`core.signature_engine` because watermarks and page
numbers are typically applied to *all* pages (or a selection) as a batch
finishing step, often chained after signing in a workflow -- see
:mod:`core.workflow_engine`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from core.page_selection import resolve_pages
from core.pdf_engine import open_pdf
from core.signature_engine import MM_TO_PT
from models.enums import PositionPreset
from utils.validation import ValidationError

_GRAY = (0.5, 0.5, 0.5)


@dataclass
class TextWatermarkOptions:
    text: str = "DRAFT"
    font_size: float = 48.0
    opacity: float = 30.0  # 0-100
    rotation_degrees: float = 45.0
    color_rgb: tuple[float, float, float] = _GRAY
    pages_expression: str = "all"


@dataclass
class ImageWatermarkOptions:
    image_path: str = ""
    width_pct: float = 40.0
    height_pct: float = 40.0
    opacity: float = 20.0
    rotation_degrees: float = 0.0
    position_preset: PositionPreset = PositionPreset.CENTRE
    pages_expression: str = "all"


@dataclass
class PageNumberOptions:
    format: str = "Page {n} of {total}"  # also supports "{n}", "{n} / {total}"
    position: PositionPreset = PositionPreset.BOTTOM_CENTRE
    font_size: float = 10.0
    start_number: int = 1
    margin_mm: float = 10.0
    pages_expression: str = "all"


def add_text_watermark(source_path: str | Path, output_path: str | Path, options: TextWatermarkOptions) -> str:
    if not options.text.strip():
        raise ValidationError("Watermark text is empty.")
    with open_pdf(source_path) as doc:
        pages = resolve_pages(options.pages_expression, doc.page_count)
        for page_no in pages:
            page = doc[page_no - 1]
            rect = page.rect
            center = fitz.Point(rect.width / 2, rect.height / 2)
            morph = (center, fitz.Matrix(options.rotation_degrees))
            page.insert_text(
                fitz.Point(rect.width / 2 - len(options.text) * options.font_size * 0.28, rect.height / 2),
                options.text,
                fontsize=options.font_size,
                fontname="helv",
                color=options.color_rgb,
                fill_opacity=max(0.0, min(1.0, options.opacity / 100.0)),
                morph=morph,
                overlay=True,
            )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)
    return str(output_path)


def add_image_watermark(source_path: str | Path, output_path: str | Path, options: ImageWatermarkOptions) -> str:
    from core.signature_engine import SignatureImageProcessor, resolve_placement
    from models.signature_template import SignatureTemplate

    template = SignatureTemplate(
        image_path=options.image_path,
        position_preset=options.position_preset,
        width_pct=options.width_pct,
        height_pct=options.height_pct,
        opacity=options.opacity,
        rotation_degrees=options.rotation_degrees,
        page_rule_expression=options.pages_expression,
    )
    prepared = SignatureImageProcessor.prepare(
        options.image_path, autocrop=False, opacity_pct=options.opacity, rotation_degrees=options.rotation_degrees
    )
    with open_pdf(source_path) as doc:
        pages = resolve_pages(options.pages_expression, doc.page_count)
        for page_no in pages:
            page = doc[page_no - 1]
            placement = resolve_placement(template, page.rect.width, page.rect.height)
            page.insert_image(placement.as_rect(), stream=prepared.png_bytes, overlay=True)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)
    return str(output_path)


@dataclass
class BatesNumberingOptions:
    """Continuous legal-style numbering (e.g. ``ABC-000001``) usable across a
    whole submission pack or a run of separate files -- pass the returned
    ``next_start_number`` from one call as the next file's ``start_number``
    to keep numbering continuous across multiple documents."""

    prefix: str = ""
    suffix: str = ""
    digit_count: int = 6
    start_number: int = 1
    position: PositionPreset = PositionPreset.BOTTOM_RIGHT
    font_size: float = 9.0
    margin_mm: float = 10.0
    pages_expression: str = "all"


@dataclass
class BatesNumberingResult:
    output_path: str
    first_number: int
    last_number: int
    next_start_number: int  # pass this as the next file's start_number to continue the sequence


def add_bates_numbering(source_path: str | Path, output_path: str | Path, options: BatesNumberingOptions) -> BatesNumberingResult:
    with open_pdf(source_path) as doc:
        total = doc.page_count
        pages = resolve_pages(options.pages_expression, total)
        margin_pt = options.margin_mm * MM_TO_PT
        current = options.start_number
        first_number = current
        for page_no in pages:
            page = doc[page_no - 1]
            label = f"{options.prefix}{str(current).zfill(options.digit_count)}{options.suffix}"
            rect = page.rect
            text_width = fitz.get_text_length(label, fontname="helv", fontsize=options.font_size)
            y = rect.height - margin_pt
            if options.position in (PositionPreset.TOP_LEFT, PositionPreset.TOP_CENTRE, PositionPreset.TOP_RIGHT):
                y = margin_pt + options.font_size
            if options.position in (PositionPreset.BOTTOM_LEFT, PositionPreset.TOP_LEFT):
                x = margin_pt
            elif options.position in (PositionPreset.BOTTOM_RIGHT, PositionPreset.TOP_RIGHT):
                x = rect.width - margin_pt - text_width
            else:
                x = (rect.width - text_width) / 2
            page.insert_text(fitz.Point(x, y), label, fontsize=options.font_size, fontname="helv", color=(0, 0, 0))
            current += 1

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)

    return BatesNumberingResult(
        output_path=str(output_path), first_number=first_number, last_number=current - 1, next_start_number=current
    )


def add_page_numbers(source_path: str | Path, output_path: str | Path, options: PageNumberOptions) -> str:
    with open_pdf(source_path) as doc:
        total = doc.page_count
        pages = resolve_pages(options.pages_expression, total)
        margin_pt = options.margin_mm * MM_TO_PT
        for page_no in pages:
            page = doc[page_no - 1]
            display_n = page_no - 1 + options.start_number
            text = options.format.replace("{n}", str(display_n)).replace("{total}", str(total))
            rect = page.rect
            text_width = fitz.get_text_length(text, fontname="helv", fontsize=options.font_size)
            y = rect.height - margin_pt
            if options.position in (PositionPreset.TOP_LEFT, PositionPreset.TOP_CENTRE, PositionPreset.TOP_RIGHT):
                y = margin_pt + options.font_size
            if options.position in (PositionPreset.BOTTOM_LEFT, PositionPreset.TOP_LEFT):
                x = margin_pt
            elif options.position in (PositionPreset.BOTTOM_RIGHT, PositionPreset.TOP_RIGHT):
                x = rect.width - margin_pt - text_width
            else:
                x = (rect.width - text_width) / 2
            page.insert_text(fitz.Point(x, y), text, fontsize=options.font_size, fontname="helv", color=(0, 0, 0))
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)
    return str(output_path)
