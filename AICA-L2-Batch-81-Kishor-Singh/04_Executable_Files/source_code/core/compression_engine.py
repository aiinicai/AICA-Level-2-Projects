"""PDF compression: downsample/re-encode embedded images, preserve text/vectors.

Text and vector content (the actual page content stream, fonts, form
fields) is never rasterized or touched here -- only embedded raster images
are recompressed, which is what actually drives file size down for typical
scanned or photo-heavy CA documents without degrading text sharpness or
searchability.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from core.pdf_engine import open_pdf


class CompressionPreset(str, Enum):
    MAXIMUM_QUALITY = "Maximum Quality"
    STANDARD = "Standard"
    EMAIL = "Email"
    MAXIMUM_COMPRESSION = "Maximum Compression"


@dataclass
class PresetSettings:
    max_dimension_px: int  # longest side; larger images are downsampled to this
    jpeg_quality: int


_PRESET_SETTINGS: dict[CompressionPreset, PresetSettings] = {
    CompressionPreset.MAXIMUM_QUALITY: PresetSettings(max_dimension_px=4000, jpeg_quality=95),
    CompressionPreset.STANDARD: PresetSettings(max_dimension_px=2000, jpeg_quality=85),
    CompressionPreset.EMAIL: PresetSettings(max_dimension_px=1200, jpeg_quality=70),
    CompressionPreset.MAXIMUM_COMPRESSION: PresetSettings(max_dimension_px=900, jpeg_quality=50),
}


@dataclass
class CompressionResult:
    output_path: str
    original_size_bytes: int
    compressed_size_bytes: int
    images_recompressed: int

    @property
    def reduction_percent(self) -> float:
        if self.original_size_bytes == 0:
            return 0.0
        return (1 - self.compressed_size_bytes / self.original_size_bytes) * 100.0


def compress_pdf(source_path: str | Path, output_path: str | Path, preset: CompressionPreset) -> CompressionResult:
    """Recompress every embedded image per the chosen preset, saved as a new file.

    If the result would be larger than the original (rare, but possible for
    already-optimized files or documents with little raster content), the
    original bytes are written to ``output_path`` instead -- compression
    never makes a file bigger.
    """
    settings = _PRESET_SETTINGS[preset]
    source_path = Path(source_path)
    original_size = source_path.stat().st_size
    images_recompressed = 0

    with open_pdf(source_path) as doc:
        seen_xrefs: set[int] = set()
        for page_index in range(doc.page_count):
            for image_info in doc.get_page_images(page_index, full=True):
                xref = image_info[0]
                if xref in seen_xrefs:
                    continue  # same image reused on multiple pages -- recompress once
                seen_xrefs.add(xref)
                try:
                    _recompress_image(doc, xref, settings)
                    images_recompressed += 1
                except Exception:  # noqa: BLE001 - a single malformed image must not abort the batch
                    continue

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = output_path.with_suffix(".tmp_compress.pdf")
        doc.save(str(temp_path), garbage=4, deflate=True)

    compressed_size = temp_path.stat().st_size
    if compressed_size >= original_size:
        # Compression didn't help (e.g. an already-optimized or text-only PDF) --
        # keep the original bytes rather than shipping a larger "compressed" file.
        output_path.write_bytes(source_path.read_bytes())
        temp_path.unlink(missing_ok=True)
        compressed_size = original_size
    else:
        temp_path.replace(output_path)

    return CompressionResult(
        output_path=str(output_path),
        original_size_bytes=original_size,
        compressed_size_bytes=compressed_size,
        images_recompressed=images_recompressed,
    )


def _recompress_image(doc: fitz.Document, xref: int, settings: PresetSettings) -> None:
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")  # JPEG has no alpha channel

    if max(img.size) > settings.max_dimension_px:
        ratio = settings.max_dimension_px / max(img.size)
        new_size = (max(1, round(img.width * ratio)), max(1, round(img.height * ratio)))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=settings.jpeg_quality, optimize=True)
    new_bytes = buf.getvalue()

    # Only replace if the recompressed version is actually smaller -- an
    # already-compressed JPEG re-encoded at a similar quality can occasionally
    # grow slightly, which would defeat the purpose of this operation.
    if len(new_bytes) < len(image_bytes):
        # compress=0 is essential: update_stream() flate-compresses its input by
        # default, which would wrap our already-JPEG-encoded bytes in an extra
        # Flate layer while the Filter key below still says "just DCTDecode" --
        # readers then try to JPEG-decode raw zlib bytes and fail outright.
        doc.update_stream(xref, new_bytes, compress=0)
        # Ensure the image object's own filter/metadata reflect the new JPEG
        # encoding rather than the original format, so viewers decode it correctly.
        doc.xref_set_key(xref, "Filter", "/DCTDecode")
        doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
        doc.xref_set_key(xref, "BitsPerComponent", "8")
        doc.xref_set_key(xref, "Width", str(img.width))
        doc.xref_set_key(xref, "Height", str(img.height))
