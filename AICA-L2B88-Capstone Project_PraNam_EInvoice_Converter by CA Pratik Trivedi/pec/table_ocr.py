"""Structure extraction for scanned invoices.

The point of this module is NOT to read text better - it is to rebuild the item TABLE, so
that a scan yields rows and columns rather than one stream of words:

    image -> preprocess (deskew, denoise, contrast, upscale)
          -> ruled-line detection (OpenCV morphology)  ... or alignment of OCR boxes
          -> cell boxes (row x column)
          -> words placed into cells by their coordinates, empty-looking cells re-OCR'd
          -> candidate tables scored, the goods/services table chosen
          -> rows, columns and a confidence for every cell

Everything runs locally: OpenCV, NumPy and the Tesseract program on this computer.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .logsetup import get_logger

log = get_logger()

MIN_WIDTH = 1700          # upscale smaller scans before OCR
LOW_CONF = 70             # below this a cell is reported for checking

HEADER_HINTS = {
    "description": [r"DESCRIPTION", r"PARTICULARS", r"ITEM", r"GOODS", r"MATERIAL", r"PRODUCT", r"SERVICE"],
    "hsn": [r"\bHSN\b", r"\bSAC\b", r"HS\s*CODE", r"HSN\s*/?\s*SAC"],
    "qty": [r"\bQTY\b", r"QUANTITY", r"\bNOS?\b", r"\bBOX", r"CARTON"],
    "unit": [r"^\s*UNIT\s*$", r"\bUOM\b", r"\bUQC\b"],
    "rate": [r"\bRATE\b", r"UNIT\s*PRICE", r"\bPRICE\b"],
    "value": [r"TAXABLE", r"\bAMOUNT\b", r"\bVALUE\b", r"ASSESSABLE"],
    "tax": [r"\bGST\b", r"\bIGST\b", r"\bCGST\b", r"\bSGST\b", r"TAX\s*%", r"\bCESS\b"],
}
# tables that are NOT the item table
NOT_ITEM = [r"BANK\s*(DETAIL|NAME|A/?C)", r"IFSC", r"ACCOUNT\s*NO", r"TERMS\s*(AND|&)\s*CONDITION",
            r"DECLARATION", r"TRANSPORT(ER)?\s*(DETAIL|NAME)", r"VEHICLE", r"E-?WAY",
            r"DETAILS\s*OF\s*(BUYER|RECEIVER|CONSIGNEE|SELLER|SUPPLIER)", r"AMOUNT\s*IN\s*WORDS",
            r"TOTAL\s*AMOUNT\s*AFTER\s*TAX", r"ROUND\s*OFF"]


@dataclass
class Cell:
    row: int
    col: int
    box: tuple[int, int, int, int]
    text: str = ""
    conf: float = 0.0


@dataclass
class Table:
    cells: list[Cell]
    xs: list[int]
    ys: list[int]
    kind: str = "ruled"                  # ruled | aligned
    score: float = 0.0
    header_row: int = 0

    @property
    def n_rows(self): return len(self.ys) - 1

    @property
    def n_cols(self): return len(self.xs) - 1

    def grid(self) -> list[list[Cell]]:
        out = [[Cell(r, c, (self.xs[c], self.ys[r], self.xs[c + 1], self.ys[r + 1]))
                for c in range(self.n_cols)] for r in range(self.n_rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.n_rows and 0 <= cell.col < self.n_cols:
                out[cell.row][cell.col] = cell
        return out

    @property
    def bbox(self):
        return (self.xs[0], self.ys[0], self.xs[-1], self.ys[-1])


@dataclass
class PageStructure:
    words: list[dict] = field(default_factory=list)     # text, x0, y0, x1, y1, conf
    table: Table | None = None
    angle: float = 0.0
    scale: float = 1.0
    notes: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ preprocessing
def _np():
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise RuntimeError(
            f"Scanned invoices need the '{getattr(e, 'name', '') or e}' package, which is not installed. "
            "Double-click install_requirements.bat in the tool's folder (or run "
            "'pip install -r requirements.txt') and try again.") from e
    return cv2, np


def preprocess(pil_image):
    try:
        return _preprocess(pil_image)
    except Exception as e:                       # any OpenCV difference: read the page as it is
        log.warning("preprocessing skipped (%s: %s)", type(e).__name__, e)
        import numpy as np
        return np.array(pil_image.convert("L")), 1.0, 0.0, ["image used without preprocessing"]


def _preprocess(pil_image):
    """Grayscale, upscale small scans, lift contrast, remove speckle, straighten.
    A clean, already-large image is left almost untouched."""
    cv2, np = _np()
    img = np.array(pil_image.convert("L"))
    notes, scale = [], 1.0
    if img.shape[1] < MIN_WIDTH:
        scale = MIN_WIDTH / img.shape[1]
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        notes.append(f"low-resolution scan upscaled x{scale:.1f}")
    if img.std() < 45:                                   # flat / photographed page
        img = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
        notes.append("contrast enhanced")
    if cv2.Laplacian(img, cv2.CV_64F).var() > 1200:      # speckle
        img = cv2.medianBlur(img, 3)
        notes.append("noise reduced")
    try:
        angle = _skew_angle(img)
    except Exception as e:
        log.warning("deskew skipped (%s: %s)", type(e).__name__, e)
        angle = 0.0
    if abs(angle) > 0.25:
        h, w = img.shape
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
        notes.append(f"deskewed {angle:+.2f} deg")
    return img, scale, angle, notes


def _skew_angle(gray) -> float:
    """Skew from the long horizontal rules, or from the text baselines if the page has none."""
    cv2, np = _np()
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    lines = cv2.HoughLinesP(bw, 1, math.pi / 1800, threshold=200,
                            minLineLength=max(120, gray.shape[1] // 6), maxLineGap=12)
    angles = []
    if lines is not None:
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            a = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(a) < 12:
                angles.append(a)
    if len(angles) < 5:
        coords = np.column_stack(np.where(bw > 0))
        if len(coords) < 100:
            return 0.0
        rect_angle = cv2.minAreaRect(coords[:, ::-1].astype("float32"))[-1]
        if rect_angle > 45:
            rect_angle -= 90
        return rect_angle if abs(rect_angle) < 12 else 0.0
    return float(np.median(angles))


def binarize(gray):
    cv2, _ = _np()
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)


# ------------------------------------------------------------------ ruled lines
def line_segments(bw):
    cv2, np = _np()
    h, w = bw.shape
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w // 50), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(15, h // 80)))
    hmask = cv2.dilate(cv2.erode(bw, hk), hk)
    vmask = cv2.dilate(cv2.erode(bw, vk), vk)
    H, V = [], []
    for mask, horiz in ((hmask, True), (vmask, False)):
        found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = found[0] if len(found) == 2 else found[1]
        for c in cnts:
            x, y, cw, ch = cv2.boundingRect(c)
            if horiz and cw > max(150, w // 12) and ch < 25:
                H.append((x, y + ch // 2, x + cw))
            elif not horiz and ch > max(60, h // 40) and cw < 25:
                V.append((x + cw // 2, y, y + ch))
    return sorted(H, key=lambda s: s[1]), sorted(V, key=lambda s: s[0])


def _cluster(values, gap):
    out = []
    for v in sorted(values):
        if not out or v - out[-1][-1] > gap:
            out.append([v])
        else:
            out[-1].append(v)
    return [int(sum(g) / len(g)) for g in out]


def ruled_tables(H, V, shape) -> list[Table]:
    """Builds tables from the ruling lines. Each horizontal strip is described by the vertical
    rules that cross it; consecutive strips with the same column pattern form one table. This
    separates the item grid from the address/bank blocks, which have a different pattern."""
    if len(H) < 3 or len(V) < 2:
        return []
    h, w = shape
    xtol = max(8, w // 150)
    ys = _cluster([s[1] for s in H], max(6, h // 300))
    if len(ys) < 3:
        return []
    strips = []
    for y0, y1 in zip(ys, ys[1:]):
        if y1 - y0 < 8:
            continue
        xs = sorted({v[0] for v in V if v[1] <= y1 - 4 and v[2] >= y0 + 4})
        xs = _cluster(xs, xtol)
        strips.append((y0, y1, xs))

    def similar(a, b):
        if not a or not b:
            return False
        near = sum(1 for x in a if any(abs(x - y) <= xtol * 2 for y in b))
        return near / max(len(a), len(b)) >= 0.6

    blocks, current = [], []
    for st in strips:
        if current and similar(current[-1][2], st[2]):
            current.append(st)
        else:
            if current:
                blocks.append(current)
            current = [st]
    if current:
        blocks.append(current)

    tables = []
    for block in blocks:
        cols = _cluster([x for _, _, xs in block for x in xs], xtol)
        if len(cols) < 3 or len(block) < 2:
            continue
        rows = [block[0][0]] + [b[1] for b in block]
        left = min(s[0] for s in H if block[0][0] - 5 <= s[1] <= block[-1][1] + 5) if H else cols[0]
        right = max(s[2] for s in H if block[0][0] - 5 <= s[1] <= block[-1][1] + 5) if H else cols[-1]
        if cols[0] > left + 30:
            cols.insert(0, left)
        if cols[-1] < right - 30:
            cols.append(right)
        tables.append(Table(cells=[], xs=cols, ys=rows, kind="ruled"))
    # also offer neighbouring blocks joined together: a header row is sometimes ruled
    # differently from the rows beneath it
    for a, b in zip(tables, tables[1:]):
        if abs(a.ys[-1] - b.ys[0]) <= 6 and abs(len(a.xs) - len(b.xs)) <= 2:
            merged_x = _cluster(a.xs + b.xs, xtol)
            tables.append(Table(cells=[], xs=merged_x, ys=a.ys + b.ys[1:], kind="ruled"))
    return tables


# ------------------------------------------------------------------ OCR words
def ocr_words(gray, ocr_exe: str = "") -> list[dict]:
    from .ocr import _prepare
    pytesseract = _prepare(ocr_exe)
    from PIL import Image
    data = pytesseract.image_to_data(Image.fromarray(gray), output_type=pytesseract.Output.DICT)
    words = []
    for i, txt in enumerate(data["text"]):
        txt = (txt or "").strip()
        if not txt:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 30:
            continue
        x, y, w, h = (int(data["left"][i]), int(data["top"][i]), int(data["width"][i]), int(data["height"][i]))
        words.append({"text": txt, "x0": x, "y0": y, "x1": x + w, "y1": y + h, "conf": conf})
    return words


def _cell_ocr(gray, box, ocr_exe: str = "") -> tuple[str, float]:
    """Read one cell on its own - used where the page-level pass found nothing in a cell
    that clearly contains ink."""
    cv2, np = _np()
    from .ocr import _prepare
    from PIL import Image
    x0, y0, x1, y1 = box
    pad = 3
    crop = gray[max(y0 + pad, 0):max(y1 - pad, y0 + 1), max(x0 + pad, 0):max(x1 - pad, x0 + 1)]
    if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
        return "", 0.0
    ink = (binarize(crop) > 0).mean()
    if ink < 0.01 or ink > 0.6:
        return "", 0.0
    pytesseract = _prepare(ocr_exe)
    big = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    data = pytesseract.image_to_data(Image.fromarray(big), config="--psm 7",
                                     output_type=pytesseract.Output.DICT)
    parts, confs = [], []
    for i, t in enumerate(data["text"]):
        t = (t or "").strip()
        if not t:
            continue
        try:
            c = float(data["conf"][i])
        except (TypeError, ValueError):
            c = -1
        if c >= 30:
            parts.append(t); confs.append(c)
    return " ".join(parts), (sum(confs) / len(confs) if confs else 0.0)


def fill_cells(table: Table, words: list[dict], gray, ocr_exe: str = "", deep: bool = True) -> Table:
    """Place each OCR word in the cell that contains its centre; re-read cells that look
    occupied but came back empty."""
    buckets: dict[tuple[int, int], list[dict]] = {}
    for w in words:
        cx, cy = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
        c = _index(table.xs, cx)
        r = _index(table.ys, cy)
        if c is None or r is None:
            continue
        buckets.setdefault((r, c), []).append(w)
    cells = []
    for (r, c), ws in buckets.items():
        ws.sort(key=lambda w: (round(w["y0"] / 12), w["x0"]))
        text = " ".join(w["text"] for w in ws)
        conf = sum(w["conf"] for w in ws) / len(ws)
        cells.append(Cell(r, c, (table.xs[c], table.ys[r], table.xs[c + 1], table.ys[r + 1]), text, conf))
    if deep:
        rows_with_text = {cell.row for cell in cells if cell.text}
        for r in sorted(rows_with_text):
            for c in range(table.n_cols):
                if (r, c) in buckets:
                    continue
                box = (table.xs[c], table.ys[r], table.xs[c + 1], table.ys[r + 1])
                text, conf = _cell_ocr(gray, box, ocr_exe)
                if text:
                    cells.append(Cell(r, c, box, text, conf))
    table.cells = cells
    return table


def _index(edges: list[int], v: float):
    for i in range(len(edges) - 1):
        if edges[i] - 2 <= v < edges[i + 1] + 2:
            return i
    return None


# ------------------------------------------------------------------ borderless tables
def aligned_table(words: list[dict], shape) -> Table | None:
    """No rules on the page: rows come from the vertical position of the words and columns
    from the x positions that repeat down the page."""
    if len(words) < 12:
        return None
    h, w = shape
    rows: dict[int, list[dict]] = {}
    heights = [wd["y1"] - wd["y0"] for wd in words]
    line_h = max(8, sorted(heights)[len(heights) // 2])
    for wd in words:
        rows.setdefault(int(((wd["y0"] + wd["y1"]) / 2) // (line_h * 0.8)), []).append(wd)
    row_keys = sorted(rows)
    starts = [wd["x0"] for k in row_keys for wd in rows[k]]
    xs = _cluster(starts, max(12, w // 120))
    if len(xs) < 3:
        return None
    xs = [max(0, xs[0] - 10)] + [int((a + b) / 2) for a, b in zip(xs, xs[1:])] + [w]
    ys = []
    for k in row_keys:
        top = min(wd["y0"] for wd in rows[k])
        ys.append(max(0, top - 3))
    ys.append(h)
    ys = _cluster(ys, max(4, line_h // 2))
    if len(ys) < 3:
        return None
    return Table(cells=[], xs=xs, ys=ys, kind="aligned")


# ------------------------------------------------------------------ choosing the item table
def score_table(table: Table) -> tuple[float, int]:
    """How much does this grid look like the goods/services table? Returns (score, header row)."""
    grid = table.grid()
    best, best_row = 0.0, 0
    for r, row in enumerate(grid[:6]):
        line = " ".join(c.text for c in row).upper()
        if not line.strip():
            continue
        hits = sum(1 for pats in HEADER_HINTS.values() if any(re.search(p, line) for p in pats))
        if any(re.search(p, line) for p in NOT_ITEM):
            hits -= 3
        if hits > best:
            best, best_row = hits, r
    if best <= 0:
        return 0.0, 0
    body = grid[best_row + 1:]
    numeric_rows = 0
    for row in body:
        vals = [c.text for c in row if c.text]
        if len(vals) >= 2 and sum(bool(re.search(r"\d", v)) for v in vals) >= 2:
            numeric_rows += 1
    whole = " ".join(c.text for row in grid for c in row).upper()
    penalty = 2 if any(re.search(p, whole) for p in NOT_ITEM[:6]) else 0
    return best * 2 + min(numeric_rows, 12) - penalty, best_row


def extract_page(pil_image, ocr_exe: str = "", deep_cells: bool = True) -> PageStructure:
    """Full pipeline for one scanned page."""
    gray, scale, angle, notes = preprocess(pil_image)
    words = ocr_words(gray, ocr_exe)
    try:
        bw = binarize(gray)
        H, V = line_segments(bw)
        candidates = ruled_tables(H, V, gray.shape)
    except Exception as e:                       # keep the OCR text even if table detection fails
        log.warning("table detection failed (%s: %s)", type(e).__name__, e)
        notes.append(f"table detection could not run on this page ({type(e).__name__})")
        candidates = []
    scored: list[tuple[float, Table, int]] = []
    for t in candidates:
        fill_cells(t, words, gray, ocr_exe, deep=False)
        s, hr = score_table(t)
        if s > 0:
            scored.append((s, t, hr))
    if not scored:
        try:
            t = aligned_table(words, gray.shape)
        except Exception as e:
            log.warning("borderless detection failed (%s: %s)", type(e).__name__, e)
            t = None
        if t is not None:
            fill_cells(t, words, gray, ocr_exe, deep=False)
            s, hr = score_table(t)
            if s > 0:
                scored.append((s, t, hr))
                notes.append("no ruled table found - columns taken from the alignment of the text")
    best = None
    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        s, best, hr = scored[0]
        best.score, best.header_row = s, hr
        if deep_cells and best.kind == "ruled":
            fill_cells(best, words, gray, ocr_exe, deep=True)
            best.score, best.header_row = score_table(best)
        notes.append(f"item table found: {best.n_rows} rows x {best.n_cols} columns ({best.kind})")
    else:
        notes.append("no item table could be recognised on this scan")
    ps = PageStructure(words=words, table=best, angle=angle, scale=scale, notes=notes)
    log.info("scan page: %s", "; ".join(notes))
    return ps
