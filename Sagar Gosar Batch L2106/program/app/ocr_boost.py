"""Seal- and stamp-aware text recovery.

Tesseract's page layout analysis treats a round seal as a picture, drops or garbles the text underneath / after it and
breaks the lines around it.  This module
  1. finds seals / stamps (coloured ink blobs + circular rings, any ink colour) with OpenCV,
  2. re-reads every text line that touches a seal with several independent image treatments
     (colour-ink removal, thick-stroke removal, local contrast, plain grey) and – when installed – a second,
     deep-learning OCR engine (RapidOCR / ONNX),
  3. for every line keeps the reading that recovers the most confident characters and splices it into the page.
Everything degrades gracefully: without OpenCV only the colour-blob detector runs, without RapidOCR only Tesseract runs.
"""
import re

import numpy as np
from PIL import Image

try:                                    # optional – installed in the portable package
    import cv2
except Exception:                       # noqa
    cv2 = None

_RAPID = None


def have_cv():
    return cv2 is not None


def rapid_engine():
    global _RAPID
    if _RAPID is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID = RapidOCR()
        except Exception:               # noqa
            _RAPID = False
    return _RAPID or None


def have_rapid():
    return rapid_engine() is not None


# ----------------------------------------------------------------------------- seal detection
def _union(boxes, gap=0):
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        out = []
        for b in boxes:
            for o in out:
                if b[0] <= o[2] + gap and o[0] <= b[2] + gap and b[1] <= o[3] + gap and o[1] <= b[3] + gap:
                    o[0], o[1], o[2], o[3] = min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]); changed = True
                    break
            else:
                out.append(b)
        boxes = out
    return boxes


def find_seals(rgb):
    """-> list of (x0, y0, x1, y1) pixel boxes of round seals / large stamps (full-resolution coordinates)."""
    if cv2 is None:
        return []
    a = np.asarray(rgb.convert("RGB")); H, W = a.shape[:2]
    S = 600.0 / W
    small = cv2.resize(a, (600, max(1, int(H * S))), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    found = []
    # 1) coloured ink (blue / violet / red / green seals, highlighter, pen)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 1] > 50) & (hsv[..., 2] > 50)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)); m = cv2.dilate(m, np.ones((9, 9), np.uint8))
    n, _lab, st, _c = cv2.connectedComponentsWithStats(m)
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if w > 0.06 * sw and h > 0.04 * sw and w < 0.6 * sw and area > 0.25 * w * h * 0.25:
            found.append((x, y, x + w, y + h))
    # 2) circular rings in any ink colour (black / grey / embossed seals)
    g = cv2.GaussianBlur(gray, (5, 5), 1.2)
    bg = float(np.percentile(gray, 90))
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3); mag = np.hypot(gx, gy) + 1e-6
    circles = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30, param1=100, param2=40, minRadius=int(0.035 * sw), maxRadius=int(0.15 * sw))
    if circles is not None:
        ang = np.linspace(0, 2 * np.pi, 120, endpoint=False); ca, sa = np.cos(ang), np.sin(ang)
        for cx, cy, r in circles[0][:40]:
            ok = 0
            for dr in (-2, 0, 2):
                xs = np.rint(cx + (r + dr) * ca).astype(int); ys = np.rint(cy + (r + dr) * sa).astype(int)
                v = (xs >= 0) & (xs < sw) & (ys >= 0) & (ys < sh)
                xs, ys, c2, s2 = xs[v], ys[v], ca[v], sa[v]
                if len(xs) < 60:
                    continue
                radial = np.abs(gx[ys, xs] * c2 + gy[ys, xs] * s2) / mag[ys, xs]
                ok = max(ok, float(np.mean((radial > 0.8) & (mag[ys, xs] > 30))))
            if ok >= 0.40:
                found.append((cx - r, cy - r, cx + r, cy + r))
    out = []
    for x0, y0, x1, y1 in _union(found, gap=4):
        p = 0.06 * max(x1 - x0, y1 - y0)
        out.append((max(0, (x0 - p) / S), max(0, (y0 - p) / S), min(W, (x1 + p) / S), min(H, (y1 + p) / S)))
    return out


# ----------------------------------------------------------------------------- image treatments of a band
def _v_clean(rgb):
    from .extract_pdf import normalise_background, remove_colour_ink
    return normalise_background(remove_colour_ink(rgb))


def _thin_only(gray):
    """Drop thick strokes (bold seal rings / lettering) and keep thin ones (printed body text)."""
    if cv2 is None:
        return gray
    a = np.asarray(gray)
    ink = (a < 150).astype(np.uint8)
    core = cv2.erode(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    thick = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    out = np.where((thick > 0), 255, a).astype(np.uint8)
    return Image.fromarray(out, "L")


def _clahe(gray):
    if cv2 is None:
        return gray
    c = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    g = c.apply(np.asarray(gray))
    _t, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(b, "L")


def _dark_only(gray):
    """Black printing is darker than most stamp ink: keep only the darkest pixels."""
    a = np.asarray(gray).astype(np.float32)
    lo = np.percentile(a, 2); thr = lo + 0.42 * (np.percentile(a, 90) - lo)
    return Image.fromarray(np.where(a < thr, a, 255).astype(np.uint8), "L")


def _variants(crop_rgb):
    # every treatment starts from the colour-ink-free reading, so readable *coloured* stamp wording never leaks into the text
    v = _v_clean(crop_rgb)
    return {"clean": v, "thin": _thin_only(v), "clahe": _clahe(v), "dark": _dark_only(v)}


# ----------------------------------------------------------------------------- readers
def _tess_words(img, lang, x0, y0, W, H, psm=6):
    import pytesseract as t
    d = t.image_to_data(img, lang=lang, config=f"--oem 1 --psm {psm}", output_type=t.Output.DICT)
    out = []
    for i, tx in enumerate(d["text"]):
        tx = (tx or "").strip()
        try:
            cf = float(d["conf"][i])
        except Exception:               # noqa
            cf = -1
        if not tx or cf < 0:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        out.append(dict(text=tx, conf=cf, x0=(x + x0) / W, y0=(y + y0) / H, x1=(x + w + x0) / W, y1=(y + h + y0) / H))
    return out


def _rapid_words(crop_rgb, x0, y0, W, H):
    eng = rapid_engine()
    if eng is None:
        return []
    try:
        res, _ = eng(np.asarray(crop_rgb.convert("RGB"))[:, :, ::-1].copy())
    except Exception:                   # noqa
        return []
    out = []
    for box, text, score in (res or []):
        try:
            sc = float(score) * 100.0
        except Exception:               # noqa
            sc = 80.0
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        toks = text.split()
        if not toks:
            continue
        total = sum(len(t) for t in toks) + (len(toks) - 1) * 0.6
        pos = bx0
        for tk in toks:
            wlen = (bx1 - bx0) * len(tk) / total
            out.append(dict(text=tk, conf=sc * 0.93, x0=(pos + x0) / W, y0=(by0 + y0) / H, x1=(pos + wlen + x0) / W, y1=(by1 + y0) / H))
            pos += wlen + (bx1 - bx0) * 0.6 / total
    return out


# ----------------------------------------------------------------------------- scoring & splicing
def _usable(w, trusted):
    """A recovered word must look like real text; only the original Tesseract words are trusted at lower confidence."""
    t = w["text"]; n = len(re.sub(r"\W", "", t))
    if not n:
        return False
    if trusted:
        return True
    if w["conf"] < 62:
        return False
    if n >= 3 and not re.search(r"[aeiouAEIOU0-9]", t):
        return False
    if n == 1 and not t.isalnum():
        return False
    return True


_WORDLIKE = re.compile(r"""^[\(\["'“‘]*([A-Za-z][A-Za-z'’\-]{2,}|[Aa]|I|[\d][\d,./%\-]*[\d%/]|\d+\.?|Rs\.?|[A-Za-z]+\d+[A-Za-z\d]*)[\)\]"'”’.,;:!?/\-]*$""")


_SHORT = {"of", "to", "in", "or", "as", "if", "is", "it", "be", "by", "on", "at", "an", "no", "so", "we", "do", "up", "us", "my", "me", "he", "am", "re", "co", "ltd"}


def _wordlike(t):
    core = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", t).lower()
    return core in _SHORT or bool(_WORDLIKE.match(t))


def _norm(t):
    return re.sub(r"\W", "", t.lower())


def _ov(a, b):
    ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]); oy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
    return ox > 0.35 * min(a["x1"] - a["x0"], b["x1"] - b["x0"]) and oy > 0.5 * min(a["y1"] - a["y0"], b["y1"] - b["y0"])


def _mean_conf(ws):
    n = sum(len(w["text"]) for w in ws)
    return sum(w["conf"] * len(w["text"]) for w in ws) / n if n else 0.0


def _merge(orig, alts, med_h, tag):
    """Keep every original word; replace a doubtful one when another treatment reads it clearly better, and fill gaps with words
    that were read confidently (or by two independent treatments).  Returns (words, n_changed)."""
    cand = [dict(w, src=name) for name, ws in alts.items() for w in ws if _usable(w, False)]
    cand.sort(key=lambda w: -w["conf"])
    clusters = []
    for w in cand:
        for c in clusters:
            if _ov(c[0], w):
                c.append(w); break
        else:
            clusters.append([w])
    result = list(orig); changed = 0
    for k, c in enumerate(clusters):
        rep = c[0]
        if not _wordlike(rep["text"]):
            continue
        support = len({m["src"] for m in c if _norm(m["text"]) == _norm(rep["text"])})
        over = [o for o in result if _ov(o, rep)]
        if over:
            oc = max(o["conf"] for o in over)
            olen = sum(len(_norm(o["text"])) for o in over)
            if (rep["conf"] >= oc + 8 and rep["conf"] >= 62 and (support >= 2 or oc < 65) and len(_norm(rep["text"])) >= 0.6 * olen
                    and _norm(rep["text"]) != _norm(" ".join(o["text"] for o in over))):
                key = over[0]["line"]
                result = [o for o in result if o not in over]
            else:
                continue
        else:
            if not ((support >= 2 and rep["conf"] >= 62) or rep["conf"] >= 82):
                continue
            cy = (rep["y0"] + rep["y1"]) / 2
            near = [o for o in result if abs((o["y0"] + o["y1"]) / 2 - cy) < 0.5 * med_h]
            key = near[0]["line"] if near else ("seal", tag, k)
        w = dict(rep); w.pop("src", None); w["line"] = key; result.append(w); changed += 1
    return result, changed


def recover(colour_page, work, words, lang="eng", use_rapid=True, log=None):
    """Re-read the areas around seals.  `colour_page` is the RGB page and `work` the cleaned grey page, both in the same geometry.
    -> (new_words, n_seals, n_words_changed)"""
    W, H = work.size
    seals = find_seals(colour_page)
    if not seals:
        return words, 0, 0
    hs = sorted(w["y1"] - w["y0"] for w in words) or [0.012]
    med_h = hs[len(hs) // 2]
    out = list(words); changed = 0
    for si, (sx0, sy0, sx1, sy1) in enumerate(seals):
        pad = 1.6 * med_h * H
        by0 = int(max(0, sy0 - pad)); by1 = int(min(H, sy1 + pad)); bx0 = int(0.03 * W); bx1 = int(0.97 * W)
        crop = colour_page.crop((bx0, by0, bx1, by1))
        inband = lambda w: by0 / H <= (w["y0"] + w["y1"]) / 2 <= by1 / H
        orig = [w for w in out if inband(w)]; rest = [w for w in out if not inband(w)]
        alts = {}
        for name, im in _variants(crop).items():
            try:
                alts[name] = _tess_words(im, lang, bx0, by0, W, H)
            except Exception:               # noqa
                pass
        merged, n = _merge(orig, alts, med_h, si)
        if use_rapid and have_rapid() and _mean_conf(merged) < 80:      # deep-learning second opinion (slower)
            alts["rapid"] = _rapid_words(crop, bx0, by0, W, H)
            merged, n = _merge(orig, alts, med_h, si)
        changed += n; out = rest + merged
    return out, len(seals), changed
