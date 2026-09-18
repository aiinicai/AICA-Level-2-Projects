"""Visual PDF page organizer: reorder, delete, rotate, duplicate, insert, extract.

Wraps a single open :class:`fitz.Document` and mutates an internal page
*order list* rather than the document itself until :meth:`save_as` is
called, so the source file is never touched and every operation is
trivially reversible before saving.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from core.pdf_engine import open_pdf
from utils.validation import ValidationError, validate_pdf_path


@dataclass
class PageThumbnail:
    position: int  # current position in the working order (0-based)
    source_index: int  # original page index in the source document this came from
    rotation: int  # cumulative rotation applied, degrees
    png_bytes: bytes
    width_pt: float
    height_pt: float


class PageOrganizer:
    """Interactive page-level editor for a single PDF, backed by PyMuPDF."""

    def __init__(self, source_path: str | Path, password: str | None = None):
        self.source_path = validate_pdf_path(source_path)
        self._doc = open_pdf(self.source_path, password)
        # order: one entry per working page -> (doc_ref_key, source_page_index, rotation)
        # doc_ref_key indexes into self._extra_docs, or -1 for the original document.
        self._extra_docs: list[fitz.Document] = []
        self._order: list[list[int]] = [[-1, i, 0] for i in range(self._doc.page_count)]

    # ------------------------------------------------------------------ queries
    @property
    def page_count(self) -> int:
        return len(self._order)

    def _doc_for(self, doc_ref: int) -> fitz.Document:
        return self._doc if doc_ref == -1 else self._extra_docs[doc_ref]

    def get_thumbnails(self, zoom: float = 0.3) -> list[PageThumbnail]:
        thumbs = []
        for pos, (doc_ref, src_idx, rotation) in enumerate(self._order):
            doc = self._doc_for(doc_ref)
            page = doc[src_idx]
            original_rotation = page.rotation
            try:
                page.set_rotation((original_rotation + rotation) % 360)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                png = pixmap.tobytes("png")
                rect = page.rect
                thumbs.append(
                    PageThumbnail(
                        position=pos,
                        source_index=src_idx,
                        rotation=rotation,
                        png_bytes=png,
                        width_pt=rect.width,
                        height_pt=rect.height,
                    )
                )
            finally:
                page.set_rotation(original_rotation)
        return thumbs

    # ---------------------------------------------------------------- mutations
    def reorder(self, new_order: list[int]) -> None:
        """``new_order`` is a permutation of current positions (0-based)."""
        if sorted(new_order) != list(range(len(self._order))):
            raise ValidationError("Invalid page order supplied.")
        self._order = [self._order[i] for i in new_order]

    def delete_pages(self, positions: list[int]) -> None:
        positions_set = set(positions)
        if len(positions_set) >= len(self._order):
            raise ValidationError("Cannot delete every page from the document.")
        self._order = [entry for i, entry in enumerate(self._order) if i not in positions_set]

    def rotate_page(self, position: int, degrees: int) -> None:
        self._order[position][2] = (self._order[position][2] + degrees) % 360

    def duplicate_page(self, position: int) -> None:
        entry = list(self._order[position])
        self._order.insert(position + 1, entry)

    def insert_blank_page(self, position: int, width_pt: float = 595.0, height_pt: float = 842.0) -> None:
        blank_doc = fitz.open()
        blank_doc.new_page(width=width_pt, height=height_pt)
        ref = len(self._extra_docs)
        self._extra_docs.append(blank_doc)
        self._order.insert(position, [ref, 0, 0])

    def insert_pdf(self, position: int, other_path: str | Path, page_expression: str = "all") -> None:
        from core.page_selection import resolve_pages

        other_path = validate_pdf_path(other_path)
        other_doc = fitz.open(str(other_path))
        ref = len(self._extra_docs)
        self._extra_docs.append(other_doc)
        pages = resolve_pages(page_expression, other_doc.page_count)
        new_entries = [[ref, p - 1, 0] for p in pages]
        self._order[position:position] = new_entries

    def extract_pages(self, positions: list[int], output_path: str | Path) -> str:
        subset = [self._order[i] for i in positions]
        return self._save_entries(subset, output_path)

    # --------------------------------------------------------------------- save
    def save_as(self, output_path: str | Path) -> str:
        return self._save_entries(self._order, output_path)

    def _save_entries(self, entries: list[list[int]], output_path: str | Path) -> str:
        if not entries:
            raise ValidationError("There are no pages to save.")
        out_doc = fitz.open()
        try:
            for doc_ref, src_idx, rotation in entries:
                doc = self._doc_for(doc_ref)
                out_doc.insert_pdf(doc, from_page=src_idx, to_page=src_idx)
                new_page = out_doc[-1]
                if rotation:
                    new_page.set_rotation((new_page.rotation + rotation) % 360)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=3, deflate=True)
        finally:
            out_doc.close()
        return str(output_path)

    def close(self) -> None:
        self._doc.close()
        for d in self._extra_docs:
            d.close()

    def __enter__(self) -> "PageOrganizer":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
