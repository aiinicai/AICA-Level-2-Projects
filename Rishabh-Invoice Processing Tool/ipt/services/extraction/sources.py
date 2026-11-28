"""Getting words out of documents: PDF text layer (PyMuPDF) or OCR (Tesseract)."""
from __future__ import annotations

import re

import os
import shutil
from pathlib import Path

from ipt.services.extraction.layout import Word

MIN_TEXT_CHARS = 40  # a page with less text than this is treated as scanned
MIN_OCR_CONF = 10   # Tesseract word confidence (0-100) below which words are ignored


class OcrUnavailable(Exception):
    pass


def pdf_text_words(path: Path) -> tuple[list[Word], int]:
    """Words from the PDF text layer. Returns (words, pages_without_text)."""
    import pymupdf
    words: list[Word] = []
    empty_pages = 0
    with pymupdf.open(path) as doc:
        for pno, page in enumerate(doc):
            page_words = page.get_text("words")
            if sum(len(w[4]) for w in page_words) < MIN_TEXT_CHARS:
                empty_pages += 1
            words += [Word(w[4], w[0], w[1], w[2], w[3], pno) for w in page_words]
    return words, empty_pages


def find_tesseract() -> str | None:
    """Locate tesseract.exe (PATH, IPT_TESSERACT env var or the usual Windows folders)."""
    import sys
    bundled = str(Path(sys.executable).parent / "tesseract" / "tesseract.exe") if getattr(sys, "frozen", False) else ""
    candidates = [os.environ.get("IPT_TESSERACT", ""), bundled, shutil.which("tesseract") or "",
                  r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return None


OCR_WIDTH_PX = 2480      # ~300 dpi for an A4 width; phone scans are resampled to this
NORM_WIDTH_PT = 595.0    # OCR word boxes are scaled to an A4 width so the parser's tolerances fit every scan


def _tesseract():
    exe = find_tesseract()
    if exe is None:
        raise OcrUnavailable("Tesseract OCR is not installed. Scanned PDFs and images need it "
                             "(see docs/OCR_SETUP.md). Digital PDFs work without it.")
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = exe
    return pytesseract


def _render(page):
    """Render a PDF page so its width is ~OCR_WIDTH_PX, whatever the page's point size.
    (Phone scans often have 1 point = 1 image pixel; a fixed 300 dpi would blow them up 4x.)"""
    import pymupdf
    from PIL import Image
    zoom = OCR_WIDTH_PX / max(page.rect.width, 1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _fit_width(img):
    from PIL import Image
    img = img.convert("RGB")
    if abs(img.width - OCR_WIDTH_PX) > OCR_WIDTH_PX * 0.15:
        h = round(img.height * OCR_WIDTH_PX / img.width)
        img = img.resize((OCR_WIDTH_PX, h), Image.LANCZOS)
    return img


def clean_image(img):
    """Prepare a scan for OCR: even out lighting and background pictures, make it black on white
    and remove table rules (they glue cells together for Tesseract). OpenCV when installed,
    otherwise a Pillow-only version that skips the rule removal."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return _clean_pil(img)
    from PIL import Image
    g = deskew(np.array(img.convert("L")))
    bg = cv2.medianBlur(g, 41)
    norm = cv2.divide(g, bg, scale=255)
    _, bw = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = 255 - bw
    span = max(g.shape[1] // 25, 20)
    rules = cv2.bitwise_or(
        cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (span, 1))),
        cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, span))))
    return Image.fromarray(255 - cv2.subtract(ink, rules))


def skew_angle(gray) -> float:
    """Angle (degrees, -4..4) that makes text rows horizontal: the rotation whose row profile is
    sharpest. Phone photos of bills are usually 1-2 degrees off, enough to mix up table rows."""
    import cv2
    import numpy as np
    small = cv2.resize(gray, (max(gray.shape[1] // 4, 1), max(gray.shape[0] // 4, 1)))
    _, ink = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = ink.shape
    best_score, best = -1.0, 0.0
    for a in np.arange(-4.0, 4.01, 0.1):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), float(a), 1)
        r = cv2.warpAffine(ink, m, (w, h), flags=cv2.INTER_NEAREST)
        score = float(np.var(r.sum(axis=1).astype(float)))
        if score > best_score:
            best_score, best = score, float(a)
    return round(best, 1)


def deskew(gray):
    import cv2
    a = skew_angle(gray)
    if abs(a) < 0.2:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)


def _clean_pil(img):
    from PIL import ImageFilter, ImageMath, ImageOps
    g = ImageOps.grayscale(img)
    small = g.resize((max(g.width // 8, 1), max(g.height // 8, 1)))
    bg = small.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3)).resize(g.size)
    norm = ImageMath.lambda_eval(lambda a: a["min"]((a["g"] * 255) / (a["b"] + 1), 255),
                                 g=g.convert("F"), b=bg.convert("F")).convert("L")
    return ImageOps.autocontrast(norm, cutoff=1)


EDGE_JUNK = "_‘’'“”\"|[]{}~`«»—–"   # table rules and quote marks OCR glues to words


def _is_noise(text: str) -> bool:
    return not any(ch.isalnum() for ch in text)


# ----------------------------------------------------------------------------- OCR engines
# Primary engine: RapidOCR with PaddleOCR PP-OCRv6 models (ONNX, CPU, Apache-2.0). On the user's 9-bill phone
# scan it read 62/63 header fields correctly versus ~53/63 for Tesseract. The models ship with IPT
# (ipt/models/ocr), so no download is needed. Tesseract stays as fallback and for the second pass.
MODELS_DIR = Path(__file__).resolve().parents[2] / "models" / "ocr"
_RAPID_LOCK = __import__("threading").RLock()   # re-entrant: _rapid_words -> _rapid


def rapid_available() -> bool:
    try:
        import rapidocr  # noqa: F401
    except ImportError:
        return False
    return (MODELS_DIR / "PP-OCRv6_rec_small.onnx").exists()


def ocr_engine() -> str:
    """'rapidocr' or 'tesseract'. IPT_OCR_ENGINE (Settings) can force one; default: RapidOCR when installed."""
    want = os.environ.get("IPT_OCR_ENGINE", "auto")
    if want == "tesseract":
        return "tesseract"
    if rapid_available():
        return "rapidocr"
    if want == "rapidocr":
        raise OcrUnavailable("RapidOCR is not installed (run install_ocr_models.bat)")
    return "tesseract"


_RAPID_LOCAL = __import__("threading").local()


def ocr_threads() -> int:
    """Pages read at the same time. One single-threaded OCR engine per page is about twice as fast as one
    engine using every core (measured: 4 pages 35 s -> 17 s on 2 cores). IPT_OCR_THREADS overrides."""
    try:
        n = int(os.environ.get("IPT_OCR_THREADS", "0"))
    except ValueError:
        n = 0
    return max(1, n or min(4, os.cpu_count() or 1))


def _rapid():
    """This thread's RapidOCR engine (each thread its own, single-threaded: no lock, no sharing)."""
    eng = getattr(_RAPID_LOCAL, "engine", None)
    if eng is None:
        from rapidocr import RapidOCR
        with _RAPID_LOCK:                      # loading the models is not thread-safe
            eng = RapidOCR(params={"Global.model_root_dir": str(MODELS_DIR), "Global.log_level": "warning",
                                   "EngineConfig.onnxruntime.intra_op_num_threads": 1})
        _RAPID_LOCAL.engine = eng
    return eng


def _rapid_words(img) -> list[Word]:
    import numpy as np
    img = _fit_width(img)
    res = _rapid()(np.array(img.convert("RGB")))
    k = NORM_WIDTH_PT / img.width
    out = []
    for box, text, _score in zip(res.boxes if res.boxes is not None else [], res.txts or (), res.scores or ()):
        t = (text or "").strip().strip(EDGE_JUNK)
        if not t or _is_noise(t):
            continue
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        out.append(Word(t, min(xs) * k, min(ys) * k, max(xs) * k, max(ys) * k, 0))
    return out


def ocr_image(img, psm: int = 6) -> list[Word]:
    """OCR one page image. Word boxes come back in points of an A4-wide page.
    First pass: RapidOCR when installed, else Tesseract psm 6 (one block, keeps rows together).
    psm 11 ('sparse text') is always Tesseract - the second pass for fields still missing."""
    if psm == 6 and ocr_engine() == "rapidocr":
        return _rapid_words(img)
    pytesseract = _tesseract()
    img = clean_image(_fit_width(img))
    data = pytesseract.image_to_data(img, lang="eng", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    k = NORM_WIDTH_PT / img.width
    out = []
    for i, t in enumerate(data["text"]):
        t = (t or "").strip().strip(EDGE_JUNK)
        conf = float(data["conf"][i])
        # Tesseract often gives clean numbers a low confidence on faded print, so only drop very weak
        # words and pure punctuation (table rules, stamps, QR noise). Amounts are cross-checked later.
        if not t or _is_noise(t) or conf < MIN_OCR_CONF:
            continue
        out.append(Word(t, data["left"][i] * k, data["top"][i] * k, (data["left"][i] + data["width"][i]) * k,
                        (data["top"][i] + data["height"][i]) * k, 0))
    return out


def ocr_words(path: Path, lang: str = "eng") -> list[Word]:
    from PIL import Image
    if ocr_engine() == "tesseract":
        _tesseract()
    words: list[Word] = []
    if path.suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(path) as doc:
            for pno, page in enumerate(doc):
                for w in ocr_image(_render(page)):
                    w.page = pno
                    words.append(w)
    else:
        with Image.open(path) as img:
            words = ocr_image(img)
    return words


def page_words(path: Path, mode: str = "auto", progress=None) -> list[tuple[list[Word], str]]:
    """[(words, method)] per page. Auto: text layer where the page has text, OCR elsewhere.
    progress(page_no, pages) is called before each page."""
    if path.suffix.lower() != ".pdf":
        if mode == "text":
            raise ValueError("Images need OCR. Use Automatic or OCR mode.")
        if progress:
            progress(0, 1)
        return [(ocr_words(path), "ocr")]
    import pymupdf
    from concurrent.futures import FIRST_COMPLETED, wait
    out: list = []
    threads = ocr_threads() if ocr_engine() == "rapidocr" else 1
    pool = _ocr_pool(threads)
    with pymupdf.open(path) as doc:
        n = len(doc)
        pending: dict = {}
        done = 0

        def collect(block: bool):
            nonlocal done
            if not pending:
                return
            finished, _ = wait(list(pending), return_when=FIRST_COMPLETED) if block else (
                [f for f in pending if f.done()], None)
            for f in finished:
                out[pending.pop(f)] = (f.result(), "ocr")
                done += 1

        for pno, page in enumerate(doc):
            if progress:
                progress(min(pno, n - 1), n)
            ws = [Word(w[4], w[0], w[1], w[2], w[3], 0) for w in page.get_text("words")]
            out.append(None)
            if mode != "ocr" and sum(len(w.text) for w in ws) >= MIN_TEXT_CHARS:
                out[pno] = (ws, "pdf_text")
                continue
            if mode == "text":
                raise ValueError(f"Page {pno + 1} has no text layer (it is a scan). Use Automatic or OCR mode.")
            img = _render(page)                 # rendering stays on this thread (PyMuPDF is not thread-safe)
            while len(pending) >= threads * 2:  # keep only a few rendered pages in memory
                collect(True)
            pending[pool.submit(ocr_image, img)] = pno
            collect(False)
        while pending:
            collect(True)
    return out


_POOLS: dict = {}


def _ocr_pool(threads: int):
    """A long-lived pool, so each thread loads its OCR engine once per IPT session, not once per file."""
    from concurrent.futures import ThreadPoolExecutor
    with _RAPID_LOCK:
        if threads not in _POOLS:
            _POOLS[threads] = ThreadPoolExecutor(threads, thread_name_prefix="ipt-ocr")
        return _POOLS[threads]


def _ocr_page(page) -> list[Word]:
    return ocr_image(_render(page))


REGION_WIDTH_PX = 3600   # zoomed render for reading one small box


def _unline(gray):
    """Blank out table rules inside a small crop (rows/columns that are mostly dark)."""
    try:
        import numpy as np
    except ImportError:
        return gray
    from PIL import Image
    a = np.array(gray).copy()
    dark = a < 128
    a[dark.mean(axis=1) > 0.5, :] = 255
    a[:, dark.mean(axis=0) > 0.6] = 255
    return Image.fromarray(a)


def read_below_label(path: Path, page_no: int, x0: float, y1: float, width: float = 110.0) -> str | None:
    """Zoom into the box just under a label (A4-point coordinates, as the OCR words) and read the
    value printed there several ways. Returned only when at least 3 readings agree and no other
    reading comes close - otherwise None (nothing is guessed)."""
    import collections
    from PIL import Image, ImageOps
    pytesseract = _tesseract()
    if path.suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(path) as doc:
            page = doc[page_no]
            z = REGION_WIDTH_PX / max(page.rect.width, 1)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    else:
        with Image.open(path) as im:
            img = im.convert("RGB").resize((REGION_WIDTH_PX, round(im.height * REGION_WIDTH_PX / im.width)))
    k = REGION_WIDTH_PX / NORM_WIDTH_PT
    tok = re.compile(r"[A-Z0-9][A-Z0-9/\-]{1,24}", re.I)
    votes: collections.Counter = collections.Counter()
    left, right = max(0.0, x0 - 6) * k, (x0 + width) * k
    for top, bottom in ((-1, 12), (-0.5, 14), (-1.5, 16)):
        g = ImageOps.autocontrast(ImageOps.grayscale(img.crop((left, (y1 + top) * k, right, (y1 + bottom) * k))),
                                  cutoff=2)
        for im in (g, _unline(g)):
            for psm in (7, 6):
                text = pytesseract.image_to_string(im, lang="eng", config=f"--psm {psm}")
                first = next((m.group(0) for m in tok.finditer(text) if re.search(r"\d", m.group(0))), None)
                if first:
                    votes[first.strip("-/")] += 1
    if not votes:
        return None
    ranked = votes.most_common(2)
    best, n = ranked[0]
    if n >= 3 and (len(ranked) == 1 or ranked[1][1] * 2 <= n):
        return best
    return None


def second_pass_words(path: Path, page_no: int) -> list[Word]:
    """Words of one page from the second OCR pass (psm 11)."""
    from PIL import Image
    if path.suffix.lower() != ".pdf":
        with Image.open(path) as img:
            return ocr_image(img, psm=11)
    import pymupdf
    with pymupdf.open(path) as doc:
        return ocr_image(_render(doc[page_no]), psm=11)


TITLE_RE = r"TAX\s*INVOI|GST\s*INVOICE|BILL\s+OF\s+SUPPLY|CREDIT\s+NOTE|DEBIT\s+NOTE|\bINVOICE\b"
END_RE = (r"AUTHORI[SZ]ED\s+SIGN|COMPUTER\s+GENERATED|JURISDICTION|TOTAL\s+AMOUNT\s+AFTER\s+TAX|NET\s+AMOUNT|"
          r"GRAND\s+TOTAL|AMOUNT\s+CHARGEABLE|RECEIVER.?S\s+SIGN|CUSTOMER.?S\s+SIGN")
CONT_NEXT_RE = r"CONTINUED\s+(TO|ON)\s+(THE\s+)?(NEXT\s+)?PAGE|\bCONTD\b|CARRIED\s+FORWARD|\bC/F\b"
PAGE_MARK_RE = r"\(\s*PAGE\s*(NO\.?\s*)?([2-9]|II)\s*\)|PAGE\s+([2-9])\s+OF\s+\d|CONTINUED\s+FROM|BROUGHT\s+FORWARD|\bB/F\b"


def _page_marks(ws) -> dict:
    import re
    text = " ".join(w.text for w in ws).upper()
    return {"title": bool(re.search(TITLE_RE, text)), "end": bool(re.search(END_RE, text)),
            "cont_next": bool(re.search(CONT_NEXT_RE, text)), "page_mark": bool(re.search(PAGE_MARK_RE, text))}


def split_invoices(pages: list[tuple[list[Word], str]]) -> list[tuple[int, int]]:
    """Group pages into invoices. Returns 0-based (first, last).

    A page starts a new invoice when it has its own invoice title, or when the previous page finished an
    invoice (signature / 'computer generated' / grand total) without saying it continues. A page marked
    'Page 2' / 'continued from' joins the previous page only if that page said it continues; otherwise it
    is a stray continuation sheet (pages scanned out of order) and stays on its own - see group_warnings."""
    marks = [_page_marks(ws) for ws, _ in pages]
    starts = []
    for i, m in enumerate(marks):
        if i == 0:
            starts.append(i)
            continue
        prev = marks[i - 1]
        if m["page_mark"]:
            new = not prev["cont_next"]
        else:
            new = m["title"] or (prev["end"] and not prev["cont_next"])
        if new:
            starts.append(i)
    return [(a, (starts[k + 1] - 1) if k + 1 < len(starts) else len(pages) - 1) for k, a in enumerate(starts)]


def group_warnings(pages: list[tuple[list[Word], str]], first: int, last: int) -> str:
    """Why an invoice's pages may be incomplete (multi-page invoice scanned out of order), else ''."""
    first_m, last_m = _page_marks(pages[first][0]), _page_marks(pages[last][0])
    if first_m["page_mark"]:
        return ("This page is a continuation sheet (e.g. 'Page 2') whose first page is not just before it "
                "in the file - totals may belong to another page. Check against the original.")
    if last_m["cont_next"]:
        return ("This invoice says it continues on the next page, but that page is not next in the file - "
                "totals may be on another page. Check against the original.")
    return ""
