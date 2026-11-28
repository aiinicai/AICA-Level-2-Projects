"""Words with positions -> text lines. Shared by the PDF text layer and OCR."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 0

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Line:
    words: list[Word]
    page: int

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def y(self) -> float:
        return sum(w.yc for w in self.words) / len(self.words)

    @property
    def x0(self) -> float:
        return self.words[0].x0

    @property
    def x1(self) -> float:
        return max(w.x1 for w in self.words)


def group_lines(words: list[Word], tolerance: float = 3.5) -> list[Line]:
    """Cluster words into visual lines (same page, similar vertical centre)."""
    lines: list[Line] = []
    for w in sorted(words, key=lambda w: (w.page, w.yc, w.x0)):
        if lines and lines[-1].page == w.page and abs(lines[-1].y - w.yc) <= tolerance:
            lines[-1].words.append(w)
        else:
            lines.append(Line([w], w.page))
    for ln in lines:
        ln.words.sort(key=lambda w: w.x0)
    return lines


def split_segments(lines: list[Line], gap: float = 24.0) -> list[Line]:
    """Split each visual line where words are far apart, so a two-column header
    ('Supplier name ......... Invoice No: 123') becomes two segments."""
    out: list[Line] = []
    for ln in lines:
        cur = [ln.words[0]]
        for w in ln.words[1:]:
            if w.x0 - cur[-1].x1 > gap:
                out.append(Line(cur, ln.page))
                cur = [w]
            else:
                cur.append(w)
        out.append(Line(cur, ln.page))
    return out
