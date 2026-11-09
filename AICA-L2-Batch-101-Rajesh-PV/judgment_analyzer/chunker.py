"""Split extracted judgment text into page-aware sections for Gemini.

Sections are built from whole pages wherever possible so page references stay
accurate. A page larger than the section limit is split on paragraph, then
sentence, then hard character boundaries. A short overlap from the previous
section is carried forward so that a finding spanning a section boundary is
not lost.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_processor import PageText

_SENTENCE_SPLIT = re.compile(r"(?<=[.;:!?])\s+")


@dataclass
class Chunk:
    index: int  # 1-based
    page_start: int
    page_end: int
    text: str  # includes [Page N] markers
    overlap_text: str = ""  # tail of the previous section, for context only

    @property
    def page_label(self) -> str:
        if self.page_start == self.page_end:
            return f"page {self.page_start}"
        return f"pages {self.page_start}-{self.page_end}"

    @property
    def char_count(self) -> int:
        return len(self.text)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token for English legal text)."""
    return max(1, len(text) // 4) if text else 0


def _split_long_text(text: str, max_chars: int) -> list[str]:
    """Split text into pieces no longer than max_chars on natural boundaries."""
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current.strip():
            pieces.append(current.strip())
        current = ""

    for para in text.split("\n\n"):
        units = [para] if len(para) <= max_chars else _SENTENCE_SPLIT.split(para)
        for j, unit in enumerate(units):
            while len(unit) > max_chars:  # pathological: no sentence breaks
                flush()
                pieces.append(unit[:max_chars])
                unit = unit[max_chars:]
            sep = "\n\n" if j == 0 else " "
            if current and len(current) + len(sep) + len(unit) > max_chars:
                flush()
            current = f"{current}{sep}{unit}" if current else unit
    flush()
    return pieces


def chunk_pages(pages: list[PageText], max_chars: int = 60_000, overlap_chars: int = 1_500) -> list[Chunk]:
    """Group pages into sections of at most ``max_chars`` characters (excluding overlap)."""
    if max_chars < 1_000:
        raise ValueError("max_chars must be at least 1,000")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be >= 0 and smaller than max_chars")

    # Expand every page into (page_number, block_text) units that each fit.
    units: list[tuple[int, str]] = []
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        marker = f"[Page {page.page_number}]\n"
        budget = max_chars - len(marker) - 40
        parts = _split_long_text(text, budget)
        for i, part in enumerate(parts):
            label = marker if len(parts) == 1 else f"[Page {page.page_number}, part {i + 1}/{len(parts)}]\n"
            units.append((page.page_number, label + part))

    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    start_page = end_page = None

    def emit():
        nonlocal buf, buf_len, start_page, end_page
        if not buf:
            return
        text = "\n\n".join(buf)
        overlap = ""
        if chunks and overlap_chars:
            overlap = chunks[-1].text[-overlap_chars:]
        chunks.append(Chunk(len(chunks) + 1, start_page, end_page, text, overlap))
        buf, buf_len, start_page, end_page = [], 0, None, None

    for page_no, block in units:
        added = len(block) + (2 if buf else 0)
        if buf and buf_len + added > max_chars:
            emit()
            added = len(block)
        buf.append(block)
        buf_len += added
        start_page = page_no if start_page is None else start_page
        end_page = page_no
    emit()
    return chunks
