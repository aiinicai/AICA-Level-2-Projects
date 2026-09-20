"""Turns a PDF or Word invoice into the same row/column grid that the Excel reader uses, so
one set of label-based mapping rules serves every input format.

PDF: words are grouped into lines, words on a line are merged into cells wherever the gap is
small, and cells are then aligned into columns by overlapping their horizontal extents (this
keeps right-aligned amount columns together and stops '12,345.00' from splitting in two).
Pages are stacked one under the other, so an item table can run across pages.

Word: paragraphs become one-cell rows and table rows become grid rows, in document order.

Scanned/image PDFs carry no text; they are reported rather than half-read.
"""
from __future__ import annotations

import re
from pathlib import Path

from .models import SourceValue
from .util import clean_text

MERGE_GAP = 7.0          # pt: words closer than this belong to the same cell
OVERLAP_MIN = 0.35       # share of the narrower cell that must overlap to share a column


class TextGrid:
    """Same surface as the Excel SheetView, so the reader cannot tell the formats apart."""

    is_text_grid = True          # rows may be split/wrapped: the reader stitches them
    field_grid = None            # grid to use for header labels (set for PDFs)

    def __init__(self, title: str, cells: dict[tuple[int, int], str], conf: dict | None = None):
        self.title = title
        self.conf_map = conf or {}
        self._cells = {k: v for k, v in cells.items() if clean_text(v)}
        self.max_row = max((r for r, _ in self._cells), default=1)
        self.max_col = max((c for _, c in self._cells), default=1)

    def bounds(self, r, c):
        return (r, c, r, c)

    def ref(self, r, c) -> str:
        return f"{self.title}!R{r}C{c}"

    def confidence(self, r, c) -> float:
        """OCR confidence for a cell (100 for text that was not OCR'd)."""
        return float(self.conf_map.get((r, c), 100.0))

    def get(self, r, c) -> SourceValue:
        return SourceValue(self._cells.get((r, c)), f"{self.title}!R{r}C{c}")

    def text(self, r, c) -> str:
        return clean_text(self._cells.get((r, c)))

    def hidden(self, r) -> bool:
        return False

    def filled(self, r) -> int:
        return sum(1 for (rr, _), v in self._cells.items() if rr == r and clean_text(v))

    def header_text(self, r, c, span=2) -> str:
        """Heading text for a column, including fragments on sparse neighbouring lines
        ('Kind of' / 'Packages' / 'GMS' printed on three lines)."""
        parts = []
        for rr in range(r - span, r + span + 1):
            t = self.text(rr, c)
            if t and (rr == r or self.filled(rr) <= 3):
                parts.append(t)
        return " ".join(parts)

    def text_cells(self):
        for (r, c), v in sorted(self._cells.items()):
            t = clean_text(v)
            if t:
                yield r, c, t


# ------------------------------------------------------------------ PDF
def _line_cells(words):
    """Merge the words of one line into cells: [(x0, x1, text), ...]."""
    out = []
    for w in sorted(words, key=lambda w: w["x0"]):
        if out and w["x0"] - out[-1][1] <= MERGE_GAP:
            x0, x1, t = out[-1]
            out[-1] = (x0, w["x1"], f"{t} {w['text']}")
        else:
            out.append((w["x0"], w["x1"], w["text"]))
    return out


def _columns(cells, page_width):
    """Group cell extents into columns. Narrow cells define the columns; wide cells (headings
    spanning several columns) are then attached to the leftmost column they cover."""
    narrow = sorted([c for c in cells if (c[1] - c[0]) <= page_width / 5], key=lambda c: c[0])
    cols: list[list[float]] = []
    for x0, x1, _ in narrow:
        for col in cols:
            ov = min(x1, col[1]) - max(x0, col[0])
            if ov > 0 and ov >= OVERLAP_MIN * min(x1 - x0, col[1] - col[0]):
                col[0], col[1] = min(col[0], x0), max(col[1], x1)
                break
        else:
            cols.append([x0, x1])
    cols.sort()
    merged: list[list[float]] = []
    for c in cols:                                   # join columns that ended up overlapping
        if merged and c[0] < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], c[1])
        else:
            merged.append(c)
    return merged or [[0, page_width]]


def _col_index(x0, x1, cols):
    best, score = 0, -1e9
    for i, (a, b) in enumerate(cols):
        ov = min(x1, b) - max(x0, a)
        if ov > score:
            best, score = i, ov
    return best + 1


def _rule_columns(page, min_len=12.0):
    """Column boundaries taken from the ruling lines of the invoice, when it has any."""
    xs = []
    for e in list(page.edges) + list(page.lines):
        try:
            x0 = float(e.get("x0", 0)); x1 = float(e.get("x1", x0))
            top = float(e.get("top", e.get("y0", 0)))
            bottom = float(e.get("bottom", e.get("y1", top)))
            if abs(x1 - x0) < 1 and abs(bottom - top) >= min_len:
                xs.append(round(x0, 1))
        except (TypeError, ValueError):
            continue
    xs = sorted(set(xs))
    out = []
    for x in xs:                                   # merge rules within 2pt of each other
        if not out or x - out[-1] > 2:
            out.append(x)
    return out


def _line_cells_from(ln, gap=MERGE_GAP):
    """Re-merge an already-split line (used to build the label grid)."""
    out = []
    for x0, x1, t in ln:
        if out and x0 - out[-1][1] <= gap:
            out[-1] = (out[-1][0], x1, f"{out[-1][2]} {t}")
        else:
            out.append((x0, x1, t))
    return out


DOC_START = re.compile(r"INVOICE\s*NO|DEBIT\s*NOTE|CREDIT\s*NOTE|BILL\s*NO", re.I)


def _words_from_chars(page):
    """Some PDFs carry no space characters, so every phrase arrives glued together
    ('DateofSupply'). The words are rebuilt from the character positions instead."""
    chars = [c for c in page.chars if (c.get("text") or "").strip()]
    if not chars:
        return []
    widths = [float(c["x1"]) - float(c["x0"]) for c in chars]
    avg = sum(widths) / len(widths)
    rows: dict[int, list] = {}
    for c in chars:
        rows.setdefault(round(float(c["top"]) / 3.0), []).append(c)
    out = []
    for k in sorted(rows):
        line, word = [], None
        for c in sorted(rows[k], key=lambda c: float(c["x0"])):
            if word and float(c["x0"]) - word[1] > avg * 0.38:
                line.append(tuple(word))
                word = None
            if word is None:
                word = [float(c["x0"]), float(c["x1"]), c["text"]]
            else:
                word[1] = float(c["x1"])
                word[2] += c["text"]
        if word:
            line.append(tuple(word))
        if line:
            out.append(line)
    return out


KEYWORDS = ("INVOICE", "TOTAL", "GST", "AMOUNT", "DATE", "NAME", "HSN", "TAX", "QTY", "RATE", "ADDRESS")


def _lines_from_chars(chars, key_x0, key_x1, key_top, reverse=False):
    """Group characters into lines and words using the supplied coordinate accessors."""
    if not chars:
        return []
    widths = [key_x1(c) - key_x0(c) for c in chars]
    avg = max(sum(widths) / len(widths), 0.5)
    rows: dict[int, list] = {}
    for c in chars:
        rows.setdefault(round(key_top(c) / 3.0), []).append(c)
    out = []
    for k in sorted(rows):
        ordered = sorted(rows[k], key=key_x0, reverse=reverse)
        line, word = [], None
        for c in ordered:
            x0, x1 = (key_x0(c), key_x1(c)) if not reverse else (-key_x1(c), -key_x0(c))
            if word and x0 - word[1] > avg * 0.38:
                line.append(tuple(word)); word = None
            if word is None:
                word = [x0, x1, c["text"]]
            else:
                word[1] = x1
                word[2] += c["text"]
        if word:
            line.append(tuple(word))
        if line:
            out.append(line)
    return out


def _score(lines) -> int:
    text = " ".join(t for ln in lines for _, _, t in ln).upper()
    return sum(text.count(k) for k in KEYWORDS)


def _rotated_lines(page):
    """Pages whose text is printed sideways (a landscape invoice saved in a portrait page).
    Coordinates are turned back and both reading directions are tried; the one that produces
    recognisable invoice words wins."""
    chars = [c for c in page.chars if (c.get("text") or "").strip()]
    H = float(page.height)
    a = _lines_from_chars(chars, lambda c: H - float(c["bottom"]), lambda c: H - float(c["top"]),
                          lambda c: float(c["x0"]))
    b = _lines_from_chars(chars, lambda c: float(c["top"]), lambda c: float(c["bottom"]),
                          lambda c: float(c["x0"]))
    return a if _score(a) >= _score(b) else b


def _page_lines(path):
    """Words of every page grouped into lines, with the page's ruling-line columns."""
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            width = float(page.width or 612)
            ruled = _rule_columns(page)
            sideways = sum(1 for c in page.chars if c.get("upright") is False) > max(10, len(page.chars) // 2)
            if sideways:
                lines = _rotated_lines(page)
                pages.append({"lines": lines, "width": float(page.height), "ruled": []})
                continue
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            glued = words and sum(1 for w in words if len(w["text"]) > 18) >= max(2, len(words) // 6)
            if glued:
                lines = _words_from_chars(page)
            else:
                rows: dict[int, list] = {}
                for w in words:
                    rows.setdefault(round(float(w["top"]) / 3.0), []).append(w)
                lines = [[(float(w["x0"]), float(w["x1"]), w["text"]) for w in sorted(rows[k], key=lambda w: w["x0"])]
                         for k in sorted(rows)]
            pages.append({"lines": lines, "width": width, "ruled": ruled if len(ruled) >= 3 else []})
    return pages


def _grid_from_lines(lines, width, ruled, title="PDF", gap=MERGE_GAP) -> TextGrid:
    gap_cells: dict[tuple[int, int], str] = {}
    gcols = _columns([c for ln in lines for c in _line_cells_from(ln, gap)], width)
    for r, ln in enumerate(lines, 1):
        for x0, x1, t in _line_cells_from(ln, gap):
            key = (r, _col_index(x0, x1, gcols))
            gap_cells[key] = (gap_cells.get(key, "") + " " + t).strip()
    cells: dict[tuple[int, int], str] = {}
    if ruled:
        import bisect
        for r, ln in enumerate(lines, 1):
            for x0, x1, t in ln:
                c = max(bisect.bisect_right(ruled, (x0 + x1) / 2), 1)
                cells[(r, c)] = (cells.get((r, c), "") + " " + t).strip()
    else:
        cols = _columns([c for ln in lines for c in _line_cells_from(ln, gap)], width)
        for r, ln in enumerate(lines, 1):
            for x0, x1, t in _line_cells_from(ln, gap):
                key = (r, _col_index(x0, x1, cols))
                cells[key] = (cells.get(key, "") + " " + t).strip()
    grid = TextGrid(title, cells)
    grid.field_grid = TextGrid(title, gap_cells) if ruled else grid
    return grid


def _ocr_pages(path, ocr_exe=""):
    from .ocr import ocr_pages
    return ocr_pages(path, ocr_exe)


def _scan_grid(path, ocr_exe: str = "", title: str = "Scan"):
    try:
        return _scan_grid_structured(path, ocr_exe, title)
    except RuntimeError:
        raise
    except Exception as e:                       # never lose the invoice over a detection problem
        from .logsetup import get_logger
        get_logger().warning("structured scan reading failed (%s: %s) - plain OCR used", type(e).__name__, e)
        pages = _ocr_pages(path, ocr_exe)
        g = _grid_from_lines([ln for p in pages for ln in p["lines"]],
                             max(p["width"] for p in pages), [], title, 3.0)
        g.scan_notes = [f"table reconstruction could not run ({type(e).__name__}); the page was read as plain text"]
        return g


def _scan_grid_structured(path, ocr_exe: str = "", title: str = "Scan"):
    """Scanned page(s): the item table is rebuilt from the ruling lines / text alignment, and
    everything outside it is read line by line so labels keep working."""
    from .ocr import page_images
    from .table_ocr import extract_page
    cells: dict[tuple[int, int], str] = {}
    conf: dict[tuple[int, int], float] = {}
    notes: list[str] = []
    table_rows: list[int] = []
    row = 0
    for img in page_images(path):
        ps = extract_page(img, ocr_exe)
        notes.extend(ps.notes)
        tb = ps.table
        box = tb.bbox if tb else (0, 0, 0, 0)
        inside = lambda w: tb is not None and box[0] - 4 <= (w["x0"] + w["x1"]) / 2 <= box[2] + 4 \
            and box[1] - 4 <= (w["y0"] + w["y1"]) / 2 <= box[3] + 4
        outside = [w for w in ps.words if not inside(w)]
        # page text (labels and their values), line by line
        lines: dict[int, list] = {}
        for w in outside:
            lines.setdefault(int((w["y0"] + w["y1"]) / 2) // 12, []).append(w)
        entries = []
        for key in sorted(lines):
            ws = sorted(lines[key], key=lambda w: w["x0"])
            entries.append((min(w["y0"] for w in ws), "line",
                            [(float(w["x0"]), float(w["x1"]), w["text"], w["conf"]) for w in ws]))
        if tb is not None:
            grid = tb.grid()
            for r, trow in enumerate(grid):
                filled = [c for c in trow if c.text]
                if not filled:
                    continue
                entries.append((tb.ys[r], "table", [(c.col + 1, c.text, c.conf) for c in filled]))
        entries.sort(key=lambda e: e[0])
        line_cells = [c for _, kind, payload in entries if kind == "line"
                      for c in _line_cells_from([(x0, x1, t) for x0, x1, t, _ in payload], 3.0)]
        width = max([c[1] for c in line_cells] + [1000])
        cols = _columns(line_cells, width)
        for _, kind, payload in entries:
            row += 1
            if kind == "line":
                merged = _line_cells_from([(x0, x1, t) for x0, x1, t, _ in payload], 3.0)
                confs = {round(x0): cf for x0, _, _, cf in payload}
                for x0, x1, t in merged:
                    c = _col_index(x0, x1, cols)
                    key = (row, c)
                    cells[key] = (cells.get(key, "") + " " + t).strip()
                    conf[key] = min(conf.get(key, 100.0), confs.get(round(x0), 100.0))
            else:
                table_rows.append(row)
                for col, text, cf in payload:
                    cells[(row, col)] = text
                    conf[(row, col)] = cf
        row += 1                                    # blank line between pages
    if not cells:
        raise RuntimeError("OCR could not find any text on this scan. Try a clearer or higher-resolution copy.")
    g = TextGrid(title, cells, conf)
    g.field_grid = g
    g.scan_notes = notes
    g.table_rows = table_rows
    return g


def load_pdf_invoices(path, ocr_exe: str = "") -> list[TextGrid]:
    """One grid per invoice. A page that carries its own document number starts a new invoice;
    a page without one is treated as the continuation of the page before it (so a two-page
    invoice stays whole, while a PDF holding 60 invoices yields 60)."""
    try:
        import pdfplumber                      # noqa: F401
    except ImportError:
        raise RuntimeError("PDF support needs the 'pdfplumber' package (pip install -r requirements.txt).")
    pages = _page_lines(path)
    if not any(p["lines"] for p in pages):
        return [_scan_grid(path, ocr_exe, "Scan")]   # scanned PDF: rebuild the table structure
    ocr = False
    groups: list[list[dict]] = []
    for i, p in enumerate(pages):
        text = " ".join(t for ln in p["lines"] for _, _, t in ln)
        if not groups or (DOC_START.search(text) and i > 0):
            groups.append([p])
        else:
            groups[-1].append(p)
    out = []
    for n, grp in enumerate(groups, 1):
        lines = [ln for p in grp for ln in p["lines"]]
        width = max(p["width"] for p in grp)
        ruled = grp[0]["ruled"]
        title = ("Scan" if ocr else "PDF") if len(groups) == 1 else \
            f"{'Scan' if ocr else 'PDF'} p{pages.index(grp[0]) + 1}"
        out.append(_grid_from_lines(lines, width, ruled, title, 3.0 if ocr else MERGE_GAP))
    return out


def load_pdf(path) -> TextGrid:
    return load_pdf_invoices(path)[0]


# ------------------------------------------------------------------ Word
def load_docx(path) -> TextGrid:
    try:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError:
        raise RuntimeError("Word support needs the 'python-docx' package (pip install -r requirements.txt).")
    d = docx.Document(str(path))
    cells, r = {}, 0
    body = d.element.body
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            t = clean_text(Paragraph(child, d).text)
            if t:
                r += 1
                cells[(r, 1)] = t
        elif tag == "tbl":
            for row in Table(child, d).rows:
                r += 1
                seen = set()
                col = 0
                for cell in row.cells:
                    col += 1
                    if cell._tc in seen:              # merged cell repeats its text
                        continue
                    seen.add(cell._tc)
                    t = clean_text(cell.text)
                    if t:
                        cells[(r, col)] = t
    if not cells:
        raise RuntimeError("No text could be read from this Word file.")
    g = TextGrid("Word", cells)
    g.field_grid = g
    return g


def load_documents(path, ocr_exe: str = "") -> list[TextGrid]:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return load_pdf_invoices(path, ocr_exe)
    if ext == ".docx":
        return [load_docx(path)]
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return [_scan_grid(path, ocr_exe, "Scan")]
    if ext in {".doc", ".xls"}:
        raise RuntimeError(f"The old {ext} format cannot be read directly. Open it and save as "
                           f"{'.docx' if ext == '.doc' else '.xlsx'} (or as PDF), then try again.")
    raise RuntimeError(f"Unsupported file type '{ext}'. Use .xlsx, .xlsm, .pdf, .docx or a scan (.png/.jpg).")


def load_document(path) -> TextGrid:
    return load_documents(path)[0]
