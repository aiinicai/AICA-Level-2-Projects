"""PDF / image / text extraction.

Pages that carry a text layer are read directly.  Scanned pages go through an OCR pipeline that
  1. straightens the page (auto-detected 90/180/270° rotation, fine de-skew),
  2. removes coloured ink (stamps, seals, highlighter) while keeping black text,
  3. flattens the background and deletes ruling lines,
  4. reads the text with Tesseract and rebuilds lines/paragraphs with their position on the page.
"""
import hashlib
import os
import re
import time
from collections import Counter

import numpy as np
from PIL import Image, ImageFilter

from .models import Block, DocText
from .textutil import clean_text, split_label


class Cancelled(Exception):
    pass


_COMMON = frozenset("""the of and to in is that for it as with be by on not or this are from at which any shall may have has had
been will would such their its all under each other upon agreement party parties between hereby herein thereof thereto
company licence license licensee licensor lessor lessee tenant landlord premises rent term period date days month
months year years pay payment amount agreed terms conditions clause shall notice written without liability right rights
whereas witness signed executed deed dated both either one two said where whose whom than then there these those
into out over after before during against being made hereof also only who but was were can must should shall""".split())

_COLOUR_KEEP_DARK = 60
_SAT = 48


# ----------------------------------------------------------------------------- helpers
def _check(cancel):
    if cancel is None:
        return
    if (hasattr(cancel, "is_set") and cancel.is_set()) or (callable(cancel) and not hasattr(cancel, "is_set") and cancel()):
        raise Cancelled()


def _tess():
    import pytesseract
    from .config import configure_tesseract
    configure_tesseract()
    return pytesseract


def apply_page_transform(img, rot=0, skew=0.0):
    """Rotate clockwise by `rot` degrees (multiples of 90) and then de-skew by `skew` degrees."""
    if rot % 360:
        img = img.rotate(-(rot % 360), expand=True, fillcolor=(255, 255, 255) if img.mode == "RGB" else 255)
    if abs(skew) >= 0.05:
        img = img.rotate(skew, resample=Image.BICUBIC, fillcolor=(255, 255, 255) if img.mode == "RGB" else 255)
    return img


def _render(path, page_no, dpi):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        return pdf[page_no - 1].render(scale=dpi / 72.0).to_pil().convert("RGB")
    finally:
        pdf.close()


def _load_image_page(path, page_no):
    im = Image.open(path)
    try:
        im.seek(page_no - 1)
    except EOFError:
        pass
    return im.convert("RGB")


def render_page_image(doc, page_no, dpi=110):
    """The page as shown to the user – rotated/de-skewed exactly as it was before OCR so highlight regions line up."""
    if doc.kind == "image":
        img = _load_image_page(doc.path, page_no)
        if dpi < 150 and max(img.size) > 1800:
            f = 1500 / max(img.size); img = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
    elif doc.kind == "pdf":
        img = _render(doc.path, page_no, dpi)
    else:
        return None
    rot, skew = doc.page_transform.get(page_no, (0, 0.0))
    return apply_page_transform(img, rot, skew)


# ----------------------------------------------------------------------------- image clean-up
def remove_colour_ink(img):
    """Suppress coloured ink (stamps, seals, highlighter) but keep black text, even where it passes under the ink.
    Translucent ink on white always keeps one bright colour channel, black text darkens all channels – so the
    brightest channel (HSV 'value') of the coloured pixels separates the two."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    mx, mn = a.max(axis=2), a.min(axis=2)
    gray = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])
    sat = (mx - mn) > _SAT
    g = np.where(sat, mx, gray)
    g = np.where(sat & (mx >= 170), 255, g)
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "L")


def normalise_background(gray):
    w, h = gray.size
    small = gray.resize((max(1, w // 8), max(1, h // 8)), Image.BILINEAR).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(6))
    bg = np.asarray(small.resize((w, h), Image.BILINEAR)).astype(np.float32)
    a = np.asarray(gray).astype(np.float32)
    out = np.clip(a / np.maximum(bg, 40) * 255.0, 0, 255)
    out = np.where(out > 200, 255, out)
    return Image.fromarray(out.astype(np.uint8), "L")


def _long_runs(mask, minlen):
    out = np.zeros_like(mask)
    m = np.pad(mask.astype(np.int8), ((0, 0), (1, 1)))
    d = np.diff(m, axis=1)
    st, en = np.argwhere(d == 1), np.argwhere(d == -1)
    keep = (en[:, 1] - st[:, 1]) >= minlen
    for (r, s), (_, e) in zip(st[keep], en[keep]):
        out[r, s:e] = True
    return out


def remove_rules(gray):
    a = np.asarray(gray)
    dark = a < 150
    h, w = dark.shape
    horiz = _long_runs(dark, max(60, int(0.07 * w)))
    vert = _long_runs(dark.T, max(60, int(0.05 * h))).T
    m = horiz | vert
    if not m.any():
        return gray
    mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    out = np.where(np.asarray(mi) > 0, 255, a).astype(np.uint8)
    return Image.fromarray(out, "L")


def estimate_skew(gray):
    w, h = gray.size
    f = min(1.0, 900.0 / max(w, h))
    small = gray.resize((max(1, int(w * f)), max(1, int(h * f))), Image.BILINEAR)
    bw = small.point(lambda p: 255 if p < 160 else 0)
    if np.asarray(bw).sum() < 255 * 200:
        return 0.0

    def score(angle):
        r = np.asarray(bw.rotate(angle, resample=Image.BILINEAR, fillcolor=0)).astype(np.float32).sum(axis=1)
        return float(np.var(r))
    best = max((score(a), a) for a in np.arange(-4.0, 4.01, 0.5))[1]
    best = max((score(a), a) for a in np.arange(best - 0.5, best + 0.51, 0.1))[1]
    return round(float(best), 2) if abs(best) >= 0.2 else 0.0


# ----------------------------------------------------------------------------- orientation
def _osd_rotation(img):
    try:
        t = _tess()
        small = img.copy(); small.thumbnail((1600, 1600))
        s = t.image_to_osd(small, config="--psm 0 -c min_characters_to_try=20")
        rot = int(re.search(r"Rotate:\s*(\d+)", s).group(1)); conf = float(re.search(r"Orientation confidence:\s*([\d.]+)", s).group(1))
        return rot, conf
    except Exception:
        return None, 0.0


def _orientation_score(img, rot):
    t = _tess()
    small = img.copy(); small.thumbnail((1600, 1600))
    im = apply_page_transform(small, rot, 0)
    d = t.image_to_data(im.convert("L"), lang="eng", config="--oem 1 --psm 3", output_type=t.Output.DICT)
    n = 0
    for i, tx in enumerate(d["text"]):
        w = re.sub(r"[^a-z]", "", tx.lower())
        if len(w) >= 2 and w in _COMMON and float(d["conf"][i]) > 30 and d["width"][i] > 1.1 * d["height"][i]:
            n += 1
    return n


def _detect_rotation(img):
    base = _orientation_score(img, 0)
    if base >= 25:
        return 0
    cands = []
    r, c = _osd_rotation(img)
    if r and c >= 1.0:
        cands.append(r)
    cands += [x for x in (180, 90, 270) if x not in cands]
    best, best_s = 0, base
    for r in cands:
        s = _orientation_score(img, r)
        if s > best_s:
            best, best_s = r, s
        if best_s >= 25 and best_s > 3 * (base + 2):
            break
    if best_s >= 6 and best_s >= 2 * (base + 2):
        return best
    return 0


# ----------------------------------------------------------------------------- OCR
def _read_words(img, lang):
    t = _tess()
    d = t.image_to_data(img, lang=lang, config="--oem 1 --psm 3 -c tessedit_do_invert=0", output_type=t.Output.DICT)
    W, H = img.size
    words = []
    for i, tx in enumerate(d["text"]):
        tx = (tx or "").strip()
        try:
            cf = float(d["conf"][i])
        except Exception:
            cf = -1
        if not tx or cf < 0:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        words.append(dict(text=tx, conf=cf, x0=x / W, y0=y / H, x1=(x + w) / W, y1=(y + h) / H,
                          line=(d["block_num"][i], d["par_num"][i], d["line_num"][i])))
    return words


def _mean_conf(words):
    if not words:
        return 0.0
    ws = [len(w["text"]) for w in words]
    return sum(w["conf"] * l for w, l in zip(words, ws)) / max(1, sum(ws))


LAST = {"seals": 0, "relined": 0}


def _ocr_image(img, lang="eng", detect_rotation=True, ignore_colour=True, enhance=True, forced_rot=None, seal_recovery=True, second_engine=True):
    """-> (words, (rot, skew), (W, H), mean_conf)"""
    if forced_rot is not None:
        rot = forced_rot % 360
    elif detect_rotation:
        rot = _detect_rotation(img)
    else:
        rot = 0
    base = apply_page_transform(img, rot, 0)
    work = remove_colour_ink(base) if ignore_colour else base.convert("L")
    skew = 0.0
    if enhance:
        work = normalise_background(work)
        work = remove_rules(work)
    skew = estimate_skew(work)
    work = apply_page_transform(work, 0, skew)
    words = _read_words(work, lang)
    conf = _mean_conf(words)
    if enhance and conf < 84:
        alt = apply_page_transform(base.convert("L"), 0, skew)
        w2 = _read_words(alt, lang); c2 = _mean_conf(w2)
        if c2 > conf + 2 and len(w2) >= 0.8 * len(words):
            words, conf = w2, c2
    LAST["seals"] = LAST["relined"] = 0
    if seal_recovery:
        try:
            from . import ocr_boost
            colour = apply_page_transform(base.convert("RGB"), 0, skew)
            words, LAST["seals"], LAST["relined"] = ocr_boost.recover(colour, work, words, lang, second_engine)
            if LAST["seals"]:
                conf = _mean_conf(words)
        except Exception:   # noqa  - recovery is a bonus; never break the normal reading
            pass
    return words, (rot, skew), work.size, round(conf, 1)


# ----------------------------------------------------------------------------- lines & paragraphs
class Line:
    __slots__ = ("words", "confs", "x0", "y0", "x1", "y1", "page", "ocr", "brk")

    def __init__(self, words, confs, x0, y0, x1, y1, page, ocr):
        self.words, self.confs, self.x0, self.y0, self.x1, self.y1, self.page, self.ocr = words, confs, x0, y0, x1, y1, page, ocr
        self.brk = False

    @property
    def text(self):
        return " ".join(self.words)


def _lines_from_ocr(words, page):
    by = {}
    for w in words:
        by.setdefault(w["line"], []).append(w)
    lines = []
    for k in by:
        ws = sorted(by[k], key=lambda w: w["x0"])
        # drop debris
        ws = [w for w in ws if not (w["conf"] < 35 and not re.search(r"[A-Za-z0-9]{2,}", w["text"]))]
        if not ws:
            continue
        lines.append(Line([w["text"] for w in ws], [w["conf"] for w in ws], min(w["x0"] for w in ws), min(w["y0"] for w in ws),
                          max(w["x1"] for w in ws), max(w["y1"] for w in ws), page, True))
    return lines


def _plausible(line):
    ws = line.words
    if not ws:
        return False
    alnum = sum(c.isalnum() for c in line.text)
    if alnum < 0.5 * max(1, len(line.text.replace(" ", ""))):
        return False
    good = sum(1 for w in ws if len(re.sub(r"[^A-Za-z]", "", w)) >= 3)
    if len(ws) <= 4 and np.mean(line.confs) < 66 and good < 2:
        return False
    if np.mean(line.confs) < 45:
        return False
    if len(ws) <= 2 and not any(len(re.sub(r"\W", "", w)) >= 3 for w in ws):
        return bool(re.fullmatch(r"[\W\d]*\d[\W\d]*", line.text))
    return True


_PAGE_NO = re.compile(r"^\W*((page|pg)\W*)?[\dIl|]+(\s*(of|/)\s*[\dIl|]+)?\W*$", re.I)
_PAGE_OF = re.compile(r"\bpage\s*[\dIl|]+\s*of\s*[\dIl|]+\b", re.I)


def _norm_head(t):
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", re.sub(r"[^\w\s]", " ", t.lower()))).strip()


def _drop_headers_footers(pages, n_pages, drop=True, known=None):
    """Remove page numbers and repeated running headers/footers from `pages` ({page: [Line]}) in place.
    Returns the set of normalised running-head strings that were removed."""
    known = set(known or ())
    found = set()
    if not drop:
        return found
    margin = lambda l: l.y1 < 0.11 or l.y0 > 0.89
    cnt = Counter()
    for pg, ls in pages.items():
        keys = {_norm_head(l.text) for l in ls if margin(l) and len(l.text) > 3}
        cnt.update(keys)
    thresh = max(2, int(0.4 * max(1, len(pages)) + 0.5))
    rep = {k for k, c in cnt.items() if c >= thresh and len(pages) >= 3 and k}
    for pg in list(pages):
        keep = []
        for l in pages[pg]:
            k = _norm_head(l.text)
            if margin(l) and (_PAGE_NO.match(l.text.strip()) or k in rep or k in known):
                if k and not _PAGE_NO.match(l.text.strip()):
                    found.add(k)
                continue
            if _PAGE_OF.search(l.text):
                l.words = [w for w in _PAGE_OF.sub(" ", l.text).split()]
                l.confs = l.confs[:len(l.words)] + [90.0] * max(0, len(l.words) - len(l.confs))
                if not l.words:
                    continue
            keep.append(l)
        pages[pg] = keep
    return found | (known & {_norm_head(l.text) for ls in pages.values() for l in ls})


_STRONG_LABEL = re.compile(r"^(\d{1,2}(\.\d{1,2}){1,4}\.?|\d{1,2}\.)$")
_SUB_LABEL = re.compile(r"^\(\s*([a-z]{1,3}|[ivxl]{1,6}|\d{1,2})\s*\)$", re.I)


def _starts_label(line, strong_only=False):
    if not line.words:
        return False
    lab, body = split_label(line.text)
    if not lab or not body:
        return False
    if _STRONG_LABEL.match(lab):
        if "." not in lab[:-1]:               # plain "12." needs a capital letter after it
            return body[:1].isupper()
        return True
    return (not strong_only) and bool(_SUB_LABEL.match(lab))


def _rows(lines):
    ls = sorted(lines, key=lambda l: (l.y0 + l.y1) / 2.0)
    rows, i = [], 0
    while i < len(ls):
        row = [ls[i]]; j = i + 1
        h = ls[i].y1 - ls[i].y0
        while j < len(ls) and abs((ls[j].y0 + ls[j].y1) / 2.0 - (ls[i].y0 + ls[i].y1) / 2.0) < 0.4 * max(h, 0.008):
            row.append(ls[j]); j += 1
        rows.append(sorted(row, key=lambda l: l.x0)); i = j
    return rows


def _sort_lines(lines, pitch=0.02):
    """Reading order: top to bottom; table bands (several columns side by side) are read cell by cell, row by row."""
    rows = _rows(lines)
    out, i = [], 0
    while i < len(rows):
        row = rows[i]
        multi = len(row) >= 2 and all(b.x0 - a.x1 > 0.02 for a, b in zip(row, row[1:]))
        if not multi:
            out += row; i += 1; continue
        cols = [l.x0 for l in row]
        band = [row]; j = i + 1
        while j < len(rows):
            r = rows[j]
            prev_bottom = max(l.y1 for l in band[-1])
            if min(l.y0 for l in r) - prev_bottom > 1.2 * pitch:
                break
            if not all(min(abs(l.x0 - c) for c in cols) < 0.03 for l in r):
                break
            band.append(r); j += 1
        cells = {c: [] for c in range(len(cols))}
        rowcells = []                               # list of {col: [lines]} per table row
        for r in band:
            idx = [min(range(len(cols)), key=lambda c: abs(r_l.x0 - cols[c])) for r_l in r]
            starts_new = 0 in idx or not rowcells
            if starts_new:
                rowcells.append({c: [] for c in range(len(cols))})
            for l, c in zip(r, idx):
                rowcells[-1][c].append(l)
        for rc in rowcells:
            for c in range(len(cols)):
                for k, l in enumerate(rc[c]):
                    l.brk = (k == 0)
                    out.append(l)
        i = j
    return out


def _paragraphs(lines, page):
    """Group the lines of one page into paragraphs."""
    if not lines:
        return []
    ys = sorted(l.y0 for l in lines)
    deltas = [b - a for a, b in zip(ys, ys[1:]) if 0.004 < b - a < 0.06]
    pitch = float(np.median(deltas)) if deltas else 0.02
    for l in lines:
        l.brk = False
    lines = _sort_lines(lines, pitch)
    rmax = max(l.x1 for l in lines)
    paras, cur = [], [lines[0]]
    for prev, l in zip(lines, lines[1:]):
        dy = l.y0 - prev.y0
        end = bool(re.search(r"[.;:,]$", prev.text.strip()))
        new = False
        if l.brk:
            new = True
        elif dy < 0.4 * pitch:                         # side by side on the same row
            new = True
        elif dy > 1.28 * pitch:                      # extra vertical space
            new = True
        elif _starts_label(l, strong_only=True):
            new = True
        elif _starts_label(l) and (end or prev.x1 < 0.88 * rmax):
            new = True
        elif prev.x1 < 0.72 * rmax and re.search(r"[.;:]$", prev.text.strip()):
            new = True
        if new:
            paras.append(cur); cur = [l]
        else:
            cur.append(l)
    paras.append(cur)
    return paras


def _merge_number_words(words, confs):
    """OCR often reads '60,00,000' as '60, 00, 000' – glue such fragments back together."""
    ow, oc = [], []
    for w, c in zip(words, confs):
        if ow and re.fullmatch(r"\d[\d,]*,", ow[-1]) and re.match(r"\d", w):
            ow[-1] += w; oc[-1] = min(oc[-1], c)
        else:
            ow.append(w); oc.append(c)
    return ow, oc


def _block_from_lines(ls, page, ocr):
    words, confs = [], []
    for l in ls:
        lw, lc = list(l.words), list(l.confs)
        if words and lw and re.search(r"[A-Za-z]-$", words[-1]) and re.match(r"[a-z]", lw[0]):
            words[-1] += lw[0]; confs[-1] = min(confs[-1], lc[0]); lw, lc = lw[1:], lc[1:]     # "quasi-" + "governmental"
        words += lw; confs += lc
    if ocr:
        words, confs = _merge_number_words(words, confs)
    text = clean_text(" ".join(words))
    if not text:
        return None
    lab, body = split_label(text)
    # keep word confidences aligned with the words of `body`
    bw = body.split()
    wc = list(confs[len(confs) - len(bw):]) if len(bw) <= len(confs) else list(confs)
    x0, y0 = min(l.x0 for l in ls), min(l.y0 for l in ls)
    x1, y1 = max(l.x1 for l in ls), max(l.y1 for l in ls)
    return Block(text=text, label=lab, body=body, kind="para", page=page, regions=[(page, x0, y0, x1, y1)],
                 conf=round(float(np.mean(confs)), 1) if confs else 100.0, word_conf=wc, ocr=ocr)


# ----------------------------------------------------------------------------- text-layer pages
def _lines_from_textlayer(page, pno):
    W, H = float(page.width), float(page.height)
    ws = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5, y_tolerance=2)
    ws = [w for w in ws if w["text"].strip()]
    if not ws:
        return [], 0
    ws.sort(key=lambda w: (round(w["top"] / 3.0), w["x0"]))
    lines, cur = [], [ws[0]]
    for w in ws[1:]:
        c = cur[-1]
        if abs(w["top"] - c["top"]) < 0.55 * (c["bottom"] - c["top"]):
            cur.append(w)
        else:
            lines.append(cur); cur = [w]
    lines.append(cur)
    out = []
    for l in lines:
        l.sort(key=lambda w: w["x0"])
        out.append(Line([w["text"] for w in l], [100.0] * len(l), min(w["x0"] for w in l) / W, min(w["top"] for w in l) / H,
                        max(w["x1"] for w in l) / W, max(w["bottom"] for w in l) / H, pno, False))
    out.sort(key=lambda l: (l.y0, l.x0)) if False else None
    return out, len(ws)


# ----------------------------------------------------------------------------- public API
def _file_info(path):
    st = os.stat(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest(), st.st_size, time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))


def _assemble(doc, page_lines, options, ocr_pages_set):
    pages = {p: list(l) for p, l in page_lines.items()}
    for p, ls in pages.items():
        if p in ocr_pages_set:
            pages[p] = [l for l in ls if _plausible(l)]
    heads = _drop_headers_footers(pages, doc.n_pages, getattr(options, "drop_headers_footers", True))
    doc.repeat_heads = sorted(heads)
    blocks = []
    for p in sorted(pages):
        for para in _paragraphs(pages[p], p):
            b = _block_from_lines(para, p, p in ocr_pages_set)
            if b is not None and (b.ocr is False or len(re.sub(r"\W", "", b.body)) >= 2):
                blocks.append(b)
    for i, b in enumerate(blocks):
        b.idx = i; b.uid = i
    doc.blocks = blocks


def extract_pdf(path, options, progress=None, cancel=None):
    import pdfplumber
    from .pages import page_count
    sha, size, mod = _file_info(path)
    n = page_count(path)
    want = [p for p in (options.pages or range(1, n + 1)) if 1 <= p <= n]
    doc = DocText(path=path, name=os.path.basename(path), kind="pdf", n_pages=n, pages_used=want,
                  excluded_pages=[p for p in range(1, n + 1) if p not in want], sha256=sha, size=size, modified=mod)
    page_lines, ocr_pages = {}, set()
    rot_over = getattr(options, "page_rotation", None) or {}
    with pdfplumber.open(path) as pdf:
        for k, p in enumerate(want):
            _check(cancel)
            if progress:
                progress(k / max(1, len(want)), f"Reading page {p} of {n}…")
            lines, nw = ([], 0)
            if not options.force_ocr and p not in rot_over:
                try:
                    lines, nw = _lines_from_textlayer(pdf.pages[p - 1], p)
                except Exception:
                    lines, nw = [], 0
            if nw >= 25:
                page_lines[p] = lines
                doc.page_words[p] = nw; doc.page_conf[p] = 100.0
                continue
            ocr_pages.add(p)
            img = _render(path, p, options.ocr_dpi)
            forced = rot_over.get(p)
            words, tr, size_px, conf = _ocr_image(img, options.ocr_lang, options.auto_rotate and forced is None, options.ignore_colour_ink,
                                                  options.enhance_scan, forced, getattr(options, 'seal_recovery', True), getattr(options, 'second_engine', True))
            _check(cancel)
            page_lines[p] = _lines_from_ocr(words, p)
            doc.page_transform[p] = tr; doc.page_pixels[p] = size_px; doc.page_conf[p] = conf; doc.page_words[p] = len(words)
            if tr[0]:
                doc.warnings.append(f"Page {p} was upside-down/sideways and has been rotated {tr[0]}° before reading.")
            if LAST["seals"]:
                doc.warnings.append(f"Page {p}: {LAST['seals']} seal/stamp area(s) detected – the lines around them were re-read with {LAST['relined'] and 'alternative image treatments' or 'extra checks'}.")
    doc.ocr_pages = sorted(ocr_pages)
    _assemble(doc, page_lines, options, ocr_pages)
    return doc


def extract_image(path, options, progress=None, cancel=None):
    sha, size, mod = _file_info(path)
    try:
        n = getattr(Image.open(path), "n_frames", 1)
    except Exception:
        n = 1
    want = [p for p in (options.pages or range(1, n + 1)) if 1 <= p <= n]
    doc = DocText(path=path, name=os.path.basename(path), kind="image", n_pages=n, pages_used=want, sha256=sha, size=size, modified=mod,
                  excluded_pages=[p for p in range(1, n + 1) if p not in want])
    page_lines = {}
    rot_over = getattr(options, "page_rotation", None) or {}
    for k, p in enumerate(want):
        _check(cancel)
        if progress:
            progress(k / max(1, len(want)), f"Reading image page {p}…")
        img = _load_image_page(path, p)
        forced = rot_over.get(p)
        words, tr, size_px, conf = _ocr_image(img, options.ocr_lang, options.auto_rotate and forced is None, options.ignore_colour_ink,
                                              options.enhance_scan, forced, getattr(options, 'seal_recovery', True), getattr(options, 'second_engine', True))
        page_lines[p] = _lines_from_ocr(words, p)
        doc.page_transform[p] = tr; doc.page_pixels[p] = size_px; doc.page_conf[p] = conf; doc.page_words[p] = len(words)
    doc.ocr_pages = list(want)
    _assemble(doc, page_lines, options, set(want))
    return doc


def extract_txt(path, options=None, progress=None, cancel=None):
    sha, size, mod = _file_info(path)
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            txt = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    blocks = []
    for para in re.split(r"\n\s*\n", txt):
        t = clean_text(para)
        if t:
            lab, body = split_label(t)
            blocks.append(Block(idx=len(blocks), uid=len(blocks), text=t, label=lab, body=body, page=1))
    return DocText(path=path, name=os.path.basename(path), kind="txt", blocks=blocks, n_pages=1, pages_used=[1], sha256=sha, size=size, modified=mod)


def reocr_page(doc, page, rotation, options):
    """Read one page again at an explicit rotation.  -> (blocks, (rot, skew), (W, H), conf, n_words)"""
    if doc.kind == "image":
        img = _load_image_page(doc.path, page)
    else:
        img = _render(doc.path, page, options.ocr_dpi)
    words, tr, size_px, conf = _ocr_image(img, options.ocr_lang, False, options.ignore_colour_ink, options.enhance_scan, rotation, getattr(options, 'seal_recovery', True), getattr(options, 'second_engine', True))
    lines = [l for l in _lines_from_ocr(words, page) if _plausible(l)]
    pages = {page: lines}
    known = set(doc.repeat_heads or [])
    _drop_headers_footers(pages, doc.n_pages, True, known)
    blocks = []
    for para in _paragraphs(pages[page], page):
        b = _block_from_lines(para, page, True)
        if b is not None and len(re.sub(r"\W", "", b.body)) >= 2:
            blocks.append(b)
    return blocks, tr, size_px, conf, len(words)
