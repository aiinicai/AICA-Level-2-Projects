"""Compare two versions of a document: text differences and rendered-page differences.

Text comparison is exact (line-level diff via ``difflib``); rendered-page
comparison is a pixel-difference heatmap useful for catching layout/image
changes that a pure text diff would miss (e.g. a stamp added, a table
redrawn). OCR uncertainty is not the same as a confirmed textual change --
callers should present the two views distinctly rather than merging them.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageChops

from core.pdf_engine import open_pdf


@dataclass
class PageTextDiff:
    page_number: int  # 1-based
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    unchanged: bool = False


@dataclass
class ComparisonResult:
    document_a_pages: int = 0
    document_b_pages: int = 0
    page_diffs: list[PageTextDiff] = field(default_factory=list)
    pages_with_changes: list[int] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return not self.pages_with_changes and self.document_a_pages == self.document_b_pages


def compare_text(path_a: str | Path, path_b: str | Path) -> ComparisonResult:
    """Line-level text diff, page by page. Pages beyond the shorter document
    are reported as fully added/removed rather than silently ignored."""
    with open_pdf(path_a) as doc_a, open_pdf(path_b) as doc_b:
        result = ComparisonResult(document_a_pages=doc_a.page_count, document_b_pages=doc_b.page_count)
        max_pages = max(doc_a.page_count, doc_b.page_count)

        for i in range(max_pages):
            text_a = doc_a[i].get_text() if i < doc_a.page_count else ""
            text_b = doc_b[i].get_text() if i < doc_b.page_count else ""
            lines_a = text_a.splitlines()
            lines_b = text_b.splitlines()

            diff = PageTextDiff(page_number=i + 1)
            matcher = difflib.SequenceMatcher(a=lines_a, b=lines_b, autojunk=False)
            for tag, a0, a1, b0, b1 in matcher.get_opcodes():
                if tag == "equal":
                    continue
                diff.removed_lines.extend(lines_a[a0:a1])
                diff.added_lines.extend(lines_b[b0:b1])

            diff.unchanged = not diff.added_lines and not diff.removed_lines
            result.page_diffs.append(diff)
            if not diff.unchanged:
                result.pages_with_changes.append(i + 1)

        return result


def render_page_diff_image(path_a: str | Path, path_b: str | Path, page_index: int, zoom: float = 1.5) -> bytes:
    """Render one page from each document and highlight pixel differences in red.

    Returns PNG bytes of document B's page with changed regions tinted red.
    Raises IndexError if ``page_index`` is out of range for either document.
    """
    with open_pdf(path_a) as doc_a, open_pdf(path_b) as doc_b:
        matrix = fitz.Matrix(zoom, zoom)
        pix_a = doc_a[page_index].get_pixmap(matrix=matrix, alpha=False)
        pix_b = doc_b[page_index].get_pixmap(matrix=matrix, alpha=False)

        img_a = Image.frombytes("RGB", (pix_a.width, pix_a.height), pix_a.samples)
        img_b = Image.frombytes("RGB", (pix_b.width, pix_b.height), pix_b.samples)

        if img_a.size != img_b.size:
            img_a = img_a.resize(img_b.size)

        diff = ImageChops.difference(img_a, img_b).convert("L")
        # Boost faint differences (anti-aliasing noise) out of the highlight.
        threshold_mask = diff.point(lambda p: 255 if p > 25 else 0)

        highlighted = img_b.copy()
        red_overlay = Image.new("RGB", img_b.size, (255, 0, 0))
        highlighted.paste(red_overlay, mask=threshold_mask)

        import io

        buf = io.BytesIO()
        highlighted.save(buf, format="PNG")
        return buf.getvalue()
