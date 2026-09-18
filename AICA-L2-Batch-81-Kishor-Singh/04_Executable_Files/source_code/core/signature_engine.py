"""Visible-image signature preparation and placement.

Two responsibilities live here:

1. :class:`SignatureImageProcessor` -- turn a raw PNG/JPG signature scan into
   a clean, correctly-sized, semi-transparent stamp (autocrop whitespace,
   resize, opacity, rotation) while preserving resolution.
2. :func:`apply_signatures_to_pdf` -- stamp one or more prepared images onto
   the resolved pages of a single PDF, using page-relative (percentage)
   coordinates so the same template looks right on A4, Letter, Legal,
   portrait or landscape pages.

This module never represents its output as a cryptographic signature -- for
that, see :mod:`core.digital_signature_engine`.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from core.page_selection import resolve_pages
from core.pdf_engine import open_pdf
from models.enums import PositionPreset
from models.signature_template import SignatureTemplate
from utils.validation import ValidationError, validate_image_path

MM_TO_PT = 2.8346456693


@dataclass
class PreparedSignature:
    """An in-memory, ready-to-embed signature image plus its intrinsic aspect ratio."""

    png_bytes: bytes
    width_px: int
    height_px: int

    @property
    def aspect_ratio(self) -> float:
        return self.width_px / self.height_px if self.height_px else 1.0


class SignatureImageProcessor:
    """Image editing pipeline for a signature/initial/stamp/seal source image."""

    @staticmethod
    def load(path: str | Path) -> Image.Image:
        validate_image_path(path)
        try:
            img = Image.open(path)
        except Exception as exc:
            raise ValidationError(f"'{Path(path).name}' is not a valid image file.") from exc
        return img.convert("RGBA")

    @staticmethod
    def autocrop(img: Image.Image, tolerance: int = 8) -> Image.Image:
        """Trim uniform white/transparent margins around the signature strokes.

        A pixel counts as "ink" when it is both non-transparent and not
        near-white -- this correctly handles PNGs with real alpha
        transparency as well as flat scans on a white sheet with no alpha.
        """
        import numpy as np  # local import: only needed for this operation

        rgba = img.convert("RGBA")
        arr = np.array(rgba)
        alpha_ch = arr[:, :, 3]
        rgb = arr[:, :, :3].astype(int)
        near_white = (rgb.sum(axis=2) >= (255 - tolerance) * 3)
        content = (alpha_ch > tolerance) & (~near_white)
        if not content.any():
            return rgba  # nothing detected as "ink"; return unchanged
        rows = content.any(axis=1)
        cols = content.any(axis=0)
        top, bottom = int(rows.argmax()), int(len(rows) - rows[::-1].argmax())
        left, right = int(cols.argmax()), int(len(cols) - cols[::-1].argmax())
        pad = 4
        left = max(0, left - pad)
        top = max(0, top - pad)
        right = min(rgba.width, right + pad)
        bottom = min(rgba.height, bottom + pad)
        return rgba.crop((left, top, right, bottom))

    @staticmethod
    def resize(img: Image.Image, width_px: int, height_px: int, maintain_aspect: bool = True) -> Image.Image:
        if maintain_aspect:
            src_ratio = img.width / img.height
            target_ratio = width_px / height_px if height_px else src_ratio
            if target_ratio > src_ratio:
                width_px = max(1, round(height_px * src_ratio))
            else:
                height_px = max(1, round(width_px / src_ratio))
        return img.resize((max(1, width_px), max(1, height_px)), Image.LANCZOS)

    @staticmethod
    def apply_opacity(img: Image.Image, opacity_pct: float) -> Image.Image:
        opacity_pct = max(0.0, min(100.0, opacity_pct))
        if opacity_pct >= 99.999:
            return img
        rgba = img.convert("RGBA")
        r, g, b, a = rgba.split()
        factor = opacity_pct / 100.0
        a = a.point(lambda p: int(p * factor))
        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def rotate(img: Image.Image, degrees: float) -> Image.Image:
        if not degrees:
            return img
        return img.rotate(degrees, expand=True, resample=Image.BICUBIC)

    @classmethod
    def prepare(
        cls,
        path: str | Path,
        *,
        autocrop: bool = True,
        target_width_px: int | None = None,
        target_height_px: int | None = None,
        maintain_aspect: bool = True,
        opacity_pct: float = 100.0,
        rotation_degrees: float = 0.0,
    ) -> PreparedSignature:
        """Run the full prep pipeline and return an embeddable, high-res PNG."""
        img = cls.load(path)
        if autocrop:
            img = cls.autocrop(img)
        if target_width_px and target_height_px:
            img = cls.resize(img, target_width_px, target_height_px, maintain_aspect)
        img = cls.apply_opacity(img, opacity_pct)
        img = cls.rotate(img, rotation_degrees)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return PreparedSignature(png_bytes=buf.getvalue(), width_px=img.width, height_px=img.height)


@dataclass
class ResolvedPlacement:
    """A signature rectangle in absolute PDF points for one specific page."""

    x_pt: float
    y_pt: float
    width_pt: float
    height_pt: float

    def as_rect(self) -> fitz.Rect:
        return fitz.Rect(self.x_pt, self.y_pt, self.x_pt + self.width_pt, self.y_pt + self.height_pt)


def resolve_placement(
    template: SignatureTemplate, page_width_pt: float, page_height_pt: float
) -> ResolvedPlacement:
    """Turn a template's percentage-based sizing/position into a page-specific rect.

    Percentages make the template portable across A4/Letter/Legal and
    portrait/landscape pages; the margin is a fixed physical distance
    (millimetres) so it looks consistent regardless of page size.
    """
    width_pt = page_width_pt * (template.width_pct / 100.0)
    height_pt = page_height_pt * (template.height_pct / 100.0)
    margin_pt = template.margin_mm * MM_TO_PT

    preset = template.position_preset
    if preset == PositionPreset.CUSTOM:
        x = page_width_pt * (template.custom_x_pct / 100.0)
        y = page_height_pt * (template.custom_y_pct / 100.0)
    elif preset == PositionPreset.BOTTOM_LEFT:
        x, y = margin_pt, page_height_pt - margin_pt - height_pt
    elif preset == PositionPreset.BOTTOM_CENTRE:
        x, y = (page_width_pt - width_pt) / 2, page_height_pt - margin_pt - height_pt
    elif preset == PositionPreset.BOTTOM_RIGHT:
        x, y = page_width_pt - margin_pt - width_pt, page_height_pt - margin_pt - height_pt
    elif preset == PositionPreset.TOP_LEFT:
        x, y = margin_pt, margin_pt
    elif preset == PositionPreset.TOP_CENTRE:
        x, y = (page_width_pt - width_pt) / 2, margin_pt
    elif preset == PositionPreset.TOP_RIGHT:
        x, y = page_width_pt - margin_pt - width_pt, margin_pt
    elif preset == PositionPreset.CENTRE:
        x, y = (page_width_pt - width_pt) / 2, (page_height_pt - height_pt) / 2
    else:
        raise ValidationError(f"Unknown position preset: {preset}")

    # Clamp fully on-page even for unusually small/custom pages.
    x = max(0.0, min(x, max(0.0, page_width_pt - width_pt)))
    y = max(0.0, min(y, max(0.0, page_height_pt - height_pt)))
    return ResolvedPlacement(x_pt=x, y_pt=y, width_pt=width_pt, height_pt=height_pt)


@dataclass
class SignatureApplication:
    """One signature layer to apply, combining its image + template placement/rule."""

    template: SignatureTemplate
    page_rule_expression: str | None = None  # overrides template.page_rule_expression when set
    prepared: PreparedSignature | None = None  # cached prepared image, filled lazily

    def effective_expression(self) -> str:
        return self.page_rule_expression or self.template.page_rule_expression

    def get_prepared(self) -> PreparedSignature:
        if self.prepared is None:
            self.prepared = SignatureImageProcessor.prepare(
                self.template.image_path,
                autocrop=False,  # cropping is a one-time editing step, not per-apply
                opacity_pct=self.template.opacity,
                rotation_degrees=self.template.rotation_degrees,
            )
        return self.prepared


@dataclass
class SigningOutcome:
    output_path: str
    total_pages: int
    signed_pages: list[int] = field(default_factory=list)


def apply_signatures_to_pdf(
    source_path: str | Path,
    output_path: str | Path,
    applications: list[SignatureApplication],
    password: str | None = None,
) -> SigningOutcome:
    """Stamp every signature layer onto its resolved pages and save a new PDF.

    The source file is opened read-only and a brand-new file is written to
    ``output_path`` (via a temp file + atomic replace performed by the
    caller) -- the original is never modified in place.
    """
    if not applications:
        raise ValidationError("No signature layers configured.")

    with open_pdf(source_path, password) as doc:
        total_pages = doc.page_count
        all_signed_pages: set[int] = set()

        for application in applications:
            expression = application.effective_expression()
            pages_1indexed = resolve_pages(expression, total_pages)
            prepared = application.get_prepared()

            for page_no in pages_1indexed:
                page = doc[page_no - 1]
                placement = resolve_placement(application.template, page.rect.width, page.rect.height)
                page.insert_image(
                    placement.as_rect(),
                    stream=prepared.png_bytes,
                    keep_proportion=False,
                    overlay=True,
                )
                all_signed_pages.add(page_no)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)

    return SigningOutcome(
        output_path=str(output_path),
        total_pages=total_pages,
        signed_pages=sorted(all_signed_pages),
    )
