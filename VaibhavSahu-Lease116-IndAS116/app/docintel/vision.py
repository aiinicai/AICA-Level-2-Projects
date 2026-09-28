"""Computer-vision pre-processing for scanned agreements (OpenCV, with a Pillow fallback).

Pipeline for a scanned page image:
  1. grayscale + denoise                      (improves OCR on phone photos / photocopies)
  2. deskew (minimum-area-rectangle on ink)    (straightens tilted scans)
  3. contrast normalisation (CLAHE)
  4. quality metrics: blur (variance of Laplacian), skew angle, ink coverage
  5. stamp / seal detection (HSV ink segmentation of blue/violet/red marks)
     -> evidence that the executed, stamped copy was provided (audit relevance)
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field

try:  # OpenCV is optional (not available as a wheel on Windows ARM64 Python)
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    HAS_CV2 = True
except Exception:  # pragma: no cover
    HAS_CV2 = False
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None  # type: ignore

from PIL import Image, ImageFilter, ImageOps


@dataclass
class VisionReport:
    width: int = 0
    height: int = 0
    skew_angle: float = 0.0
    blur_score: float = 0.0
    blurry: bool = False
    ink_ratio: float = 0.0
    stamps: list = field(default_factory=list)       # [{"bbox": [x0,y0,x1,y1] (0..1), "colour": "blue"}]
    engine: str = "opencv" if HAS_CV2 else "pillow"
    notes: list = field(default_factory=list)


def pil_to_cv(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv_to_pil(arr) -> Image.Image:
    if len(arr.shape) == 2:
        return Image.fromarray(arr)
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def _deskew_angle(gray) -> float:
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    # use only text-like horizontal structures
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    dil = cv2.dilate(thr, kernel, iterations=1)
    lines = cv2.HoughLinesP(dil, 1, math.pi / 1800, threshold=200, minLineLength=gray.shape[1] // 6, maxLineGap=20)
    angles = []
    if lines is not None and len(lines):
        # OpenCV 4.x returns (N, 1, 4); OpenCV 5.x returns (N, 4)
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            if x2 == x1:
                continue
            a = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(a) < 15:
                angles.append(a)
    if angles:
        angles.sort()
        return float(angles[len(angles) // 2])
    coords = np.column_stack(np.where(thr > 0))
    if len(coords) < 50:
        return 0.0
    ang = cv2.minAreaRect(coords.astype(np.float32))[-1]
    if ang < -45:
        ang = 90 + ang
    elif ang > 45:
        ang = ang - 90
    return float(-ang) if abs(ang) < 15 else 0.0


def detect_stamps(bgr) -> list[dict]:
    """Coloured ink marks (rubber stamps / seals / e-stamp prints) — returns normalised bboxes."""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    masks = {
        "blue/violet": cv2.inRange(hsv, (95, 60, 40), (160, 255, 255)),
        "red": cv2.bitwise_or(cv2.inRange(hsv, (0, 80, 60), (10, 255, 255)), cv2.inRange(hsv, (170, 80, 60), (180, 255, 255))),
    }
    out = []
    for colour, mask in masks.items():
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)), iterations=2)
        found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = found[-2] if len(found) == 3 else found[0]    # OpenCV 3.x returned (image, contours, hierarchy)
        for c in cnts:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            if area < 0.002 * w * h or area > 0.25 * w * h:
                continue
            ar = cw / float(ch) if ch else 0
            if not (0.33 <= ar <= 3.0):
                continue
            fill = cv2.contourArea(c) / float(area) if area else 0
            out.append({"bbox": [round(x / w, 4), round(y / h, 4), round((x + cw) / w, 4), round((y + ch) / h, 4)],
                        "colour": colour, "fill": round(fill, 3)})
    return out


def preprocess(img: Image.Image, deskew: bool = True, detect_marks: bool = True) -> tuple[Image.Image, VisionReport]:
    """Return an OCR-ready image and a quality report."""
    rep = VisionReport(width=img.width, height=img.height)
    if not HAS_CV2:
        g = ImageOps.grayscale(img)
        g = ImageOps.autocontrast(g, cutoff=1)
        g = g.filter(ImageFilter.MedianFilter(size=3))
        rep.notes.append("OpenCV not available — Pillow fallback (no deskew / stamp detection).")
        return g.convert("RGB"), rep
    bgr = pil_to_cv(img)
    if detect_marks:
        try:
            rep.stamps = detect_stamps(bgr)
        except Exception as exc:  # pragma: no cover
            rep.notes.append(f"Stamp detection skipped: {exc}")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    rep.blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    rep.blurry = rep.blur_score < 60.0
    if rep.blurry:
        rep.notes.append("Image appears blurred — OCR accuracy may be reduced; request a clearer scan.")
    work = bgr
    if deskew:
        try:
            ang = _deskew_angle(gray)
        except Exception as exc:  # never let image clean-up stop the reading of a document
            ang = 0.0
            rep.notes.append(f"Deskew skipped: {type(exc).__name__}")
        rep.skew_angle = round(ang, 2)
        if abs(ang) > 0.3:
            (h, w) = bgr.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), ang, 1.0)
            work = cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            rep.notes.append(f"Deskewed by {ang:.2f}°.")
    g2 = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    thr = cv2.threshold(g2, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    rep.ink_ratio = round(float((thr > 0).mean()), 4)
    ink = g2[thr > 0]
    paper = g2[thr == 0]
    contrast = float(paper.mean() - ink.mean()) if ink.size and paper.size else 255.0
    # Contrast enhancement only for faint / low-contrast scans. Heavy denoising and CLAHE on clean scans
    # merge inter-character gaps and make the recogniser drop word spaces, so they are not applied by default.
    if contrast < 90 or rep.blurry:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        g3 = clahe.apply(g2)
        work = cv2.cvtColor(g3, cv2.COLOR_GRAY2BGR)
        rep.notes.append("Low contrast — CLAHE enhancement applied.")
    return cv_to_pil(work), rep


def image_from_bytes(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def to_png_bytes(img: Image.Image, max_width: int = 1400) -> bytes:
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
