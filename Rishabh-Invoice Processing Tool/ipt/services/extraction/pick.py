"""Read the word (or line) under a point of a document page - used by the review screen: the user clicks the
number on the bill image and it goes into the field they are editing. Text PDFs use their text layer; scans are
read by OCR of a small strip around the point (no guessing: if nothing is read there, nothing is returned)."""
from __future__ import annotations

from pathlib import Path


def text_at(path: Path, page: int, fx: float, fy: float, whole_line: bool = False) -> str:
    """fx, fy: the point as a fraction (0..1) of the page width / height."""
    path = Path(path)
    saved = _saved_words(path, page)
    if saved is not None:
        words, height = saved
        return _pick(words, fx * 595, fy * height, whole_line, height)
    if path.suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(path) as doc:
            p = doc[page]
            W, H = p.rect.width, p.rect.height
            words = p.get_text("words")
            if words:
                x, y = fx * W, fy * H
                return _pick([(w[4], w[0], w[1], w[2], w[3]) for w in words], x, y, whole_line, H)
            pix = p.get_pixmap(dpi=300)
            from PIL import Image
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    else:
        from PIL import Image
        img = Image.open(path).convert("RGB")
    return _ocr_strip(img, fx, fy, whole_line)


def _saved_words(path: Path, page: int):
    """Words of the extraction's own OCR (kept as <document>.ocr.json), split into single words, and the page
    height in the same 595-wide units. None if not available."""
    import json
    f = Path(str(path) + ".ocr.json")
    if not f.is_file():
        return None
    try:
        pages = json.loads(f.read_text(encoding="utf-8"))
        boxes = pages[page]
    except (OSError, ValueError, IndexError):
        return None
    height = _page_height(path, page)
    out = []
    for text, x0, y0, x1, y1 in boxes:
        parts = text.split()
        if len(parts) <= 1:
            out.append((text, x0, y0, x1, y1))
            continue
        per = (x1 - x0) / max(1, len(text))         # OCR line box: share its width by characters
        pos = x0
        for p in parts:
            out.append((p, pos, y0, pos + per * len(p), y1))
            pos += per * (len(p) + 1)
    return out, height


def _page_height(path: Path, page: int) -> float:
    if path.suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(path) as doc:
            r = doc[page].rect
            return 595 * r.height / r.width
    from PIL import Image
    with Image.open(path) as im:
        return 595 * im.height / im.width


def _pick(words, x, y, whole_line, H) -> str:
    """words: (text, x0, y0, x1, y1). The word containing the point, else the nearest on that line."""
    tol = max(2.0, H * 0.004)
    on_line = [w for w in words if w[2] - tol <= y <= w[4] + tol]
    if not on_line:
        return ""
    hit = next((w for w in on_line if w[1] - tol <= x <= w[3] + tol), None)
    if hit is None:
        hit = min(on_line, key=lambda w: min(abs(w[1] - x), abs(w[3] - x)))
        if min(abs(hit[1] - x), abs(hit[3] - x)) > H * 0.03:
            return ""
    if not whole_line:
        return hit[0]
    # the run of words around the hit with small gaps (one column of the line)
    row = sorted((w for w in on_line if abs((w[2] + w[4]) / 2 - (hit[2] + hit[4]) / 2) <= tol * 2),
                 key=lambda w: w[1])
    i = row.index(hit)
    gap = H * 0.02
    a = i
    while a > 0 and row[a][1] - row[a - 1][3] <= gap:
        a -= 1
    b = i
    while b < len(row) - 1 and row[b + 1][1] - row[b][3] <= gap:
        b += 1
    return " ".join(w[0] for w in row[a:b + 1])


def _ocr_strip(img, fx, fy, whole_line) -> str:
    from ipt.services.extraction.sources import ocr_image
    W, H = img.size
    cx, cy = int(fx * W), int(fy * H)
    # a generous strip, read as plain greyscale: on the sample scans the cleaned (binarised) small crop misread
    # '2424/26-27' and '25,983.00'; this setting read both correctly
    half_w, half_h = int(W * 0.25), max(int(H * 0.04), 40)
    box = (max(0, cx - half_w), max(0, cy - half_h), min(W, cx + half_w), min(H, cy + half_h))
    crop = img.crop(box)
    words = ocr_image(crop.convert("L"))
    if not words:
        return ""
    k = 595 / crop.width                      # ocr_image gives coordinates on a 595-wide page
    x, y = (cx - box[0]) * k, (cy - box[1]) * k
    return _pick([(w.text, w.x0, w.y0, w.x1, w.y1) for w in words], x, y, whole_line, crop.height * k)
