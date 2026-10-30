"""Detect a judgment's numbered paragraphs and add "[Para N]" markers.

Indian court and tribunal orders number their paragraphs ("12. The assessee
contends ..."), and practitioners cite them as "para 12". Page numbers alone are
less useful because the same order is reprinted with different pagination.

Detection is deliberately conservative: a number at the start of a line is
accepted as a paragraph number only if it continues the running sequence
(the next number, or a jump of at most ``MAX_JUMP`` to tolerate a missed line).
Numbered sub-lists inside a paragraph ("1. ... 2. ...") restart at 1 and are
therefore ignored once the main sequence has passed them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .pdf_processor import PageText

# "12. Text", "12 . Text", "(12) Text", "12) Text" at the start of a line.
_PARA_START = re.compile(r"^\s*\(?(\d{1,3})\s?[.)]\s+(?=[\"“'‘(A-Za-z])")
MAX_JUMP = 3


@dataclass(frozen=True)
class ParaMark:
    number: int
    page: int
    line: int  # 0-based line index within the page text


def detect_paragraphs(pages: list[PageText]) -> list[ParaMark]:
    """Return the paragraph numbers that form the judgment's main running sequence."""
    marks: list[ParaMark] = []
    last = 0
    for page in pages:
        for i, line in enumerate(page.text.splitlines()):
            m = _PARA_START.match(line)
            if not m:
                continue
            n = int(m.group(1))
            if last == 0:
                if n in (1, 2):  # a judgment's first numbered paragraph
                    marks.append(ParaMark(n, page.page_number, i))
                    last = n
            elif last < n <= last + MAX_JUMP:
                marks.append(ParaMark(n, page.page_number, i))
                last = n
    # Fewer than three paragraphs is more likely a short list than a numbered judgment.
    return marks if len(marks) >= 3 else []


def add_para_markers(pages: list[PageText], marks: list[ParaMark]) -> list[PageText]:
    """Copies of ``pages`` with "[Para N] " inserted at the start of each detected paragraph."""
    by_page: dict[int, dict[int, int]] = {}
    for mk in marks:
        by_page.setdefault(mk.page, {})[mk.line] = mk.number
    out = []
    for page in pages:
        lines_at = by_page.get(page.page_number)
        if not lines_at:
            out.append(page)
            continue
        lines = page.text.splitlines()
        for idx, number in lines_at.items():
            if idx < len(lines):
                lines[idx] = f"[Para {number}] {lines[idx].lstrip()}"
        out.append(replace(page, text="\n".join(lines)))
    return out


def para_page_map(marks: list[ParaMark]) -> dict[int, int]:
    """{paragraph number: page on which it starts}"""
    return {m.number: m.page for m in marks}
