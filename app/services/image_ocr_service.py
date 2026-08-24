# =============================================================================
# image_ocr_service.py  -  Handwritten Register Photo -> Accounting Fields
# =============================================================================
# Pipeline  (1 full-page OCR scan + 2-pass per-row amount crop only):
#
#   validate_image          PIL integrity + OpenCV decode
#   optimize_image          Downscale large phone photos to <=1600 px
#   run_full_page_ocr       Single EasyOCR pass -> spatial token list
#   detect_column_bounds    Particulars / Folio-skip / Amount columns
#   group_tokens_into_rows  Y-coordinate spatial grouping
#   extract_amount_from_crop 2-pass OCR on isolated Amount column crop
#   classify_description    Keyword + fuzzy match -> accounting category
#   map_rows_to_fields      Category -> field, aggregate site expenses
#   parse_image_to_dict     Main entry point (called by API)
#   parse_image_to_dataframe DataFrame wrapper (import service)
#
# Column layout  (standard Indian accounts register):
#   Date         0  -  8 %   image width
#   Particulars  8  - 62 %   handwritten description
#   Folio / Pg  62  - 72 %   small reference numbers  <-- SKIPPED
#   Amount Rs   72  - 90 %   main handwritten figure
#   Amount P    90  - 97 %   paise / cents
# =============================================================================

import io
import re
import math
import base64
import logging
import difflib
import numpy as np
import pandas as pd
import cv2
from PIL import Image
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter

logger = logging.getLogger("ocr_service")

# ---------------------------------------------------------------------------
# EasyOCR singleton
# ---------------------------------------------------------------------------
_EASYOCR_READER = None


def _get_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        try:
            import easyocr
            _EASYOCR_READER = easyocr.Reader(["en"], gpu=False)
            logger.info("EasyOCR reader initialized (CPU)")
        except Exception as exc:
            logger.warning("EasyOCR unavailable: %s", exc)
            _EASYOCR_READER = False
    return _EASYOCR_READER if _EASYOCR_READER is not False else None


def get_easyocr_reader():
    """Legacy public alias."""
    return _get_reader()


# ===========================================================================
# Image validation
# ===========================================================================

def _decode_to_bgr(image_bytes: bytes) -> Tuple[Optional[np.ndarray], str, str]:
    """
    Decode phone/WhatsApp photos to BGR.
    OpenCV first, then PIL (RGBA / P / CMYK). Never uses Image.verify(),
    which rejects many valid WhatsApp JPEGs.
    Returns (img, format, error).
    """
    if not image_bytes:
        return None, "UNKNOWN", "Empty image buffer"

    fmt = "UNKNOWN"
    try:
        pil = Image.open(io.BytesIO(image_bytes))
        fmt = pil.format or "UNKNOWN"
        pil.close()
    except Exception:
        pass

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is not None and img.size > 0:
        return img, fmt, ""

    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    if img is not None and img.size > 0:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img, fmt, ""

    try:
        pil = Image.open(io.BytesIO(image_bytes))
        fmt = pil.format or fmt
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        arr = np.array(pil)
        if arr.ndim == 2:
            return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR), fmt, ""
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR), fmt, ""
    except Exception as exc:
        return None, fmt, str(exc) or "Could not decode image"


def validate_image(image_bytes: bytes) -> Dict[str, Any]:
    """Validate and decode a register photo. Returns result dict."""
    img, fmt, err = _decode_to_bgr(image_bytes)
    if img is None or img.size == 0:
        return {"valid": False, "error": err or "Could not decode image"}
    h, w = img.shape[:2]
    return {"valid": True, "format": fmt, "mode": "RGB",
            "w": float(w), "h": float(h), "cv_img": img}


def validate_and_decode_image(image_bytes: bytes) -> Dict[str, Any]:
    """Legacy alias."""
    return validate_image(image_bytes)


# ===========================================================================
# Image optimisation
# ===========================================================================

def optimize_image(
    image_bytes: bytes, max_dim: int = 1600
) -> Tuple[bytes, Optional[np.ndarray], float, float]:
    """Resize phone photos: downscale huge shots, upscale small crops."""
    if not image_bytes:
        return image_bytes, None, 1000.0, 1000.0
    try:
        img, _, _ = _decode_to_bgr(image_bytes)
        if img is None:
            return image_bytes, None, 1000.0, 1000.0
        h, w = img.shape[:2]
        longest = max(h, w)
        if longest > max_dim:
            scale = max_dim / float(longest)
            nw, nh = int(w * scale), int(h * scale)
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
            _, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            return buf.tobytes(), img, float(nw), float(nh)
        if longest < 1400:
            scale = 1600.0 / float(longest)
            nw, nh = int(w * scale), int(h * scale)
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_CUBIC)
            _, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            return buf.tobytes(), img, float(nw), float(nh)
        return image_bytes, img, float(w), float(h)
    except Exception:
        return image_bytes, None, 1000.0, 1000.0


# ===========================================================================
# Ledger-page preprocessing  (deskew, lighting, highlighter, grid)
# ===========================================================================

def _neutralize_highlighter(img: np.ndarray) -> np.ndarray:
    """Replace yellow marker ink with nearby paper color so digits stay readable."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (18, 40, 90), (42, 255, 255))
    if int(cv2.countNonZero(mask)) < 80:
        return img
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.dilate(mask, kernel, iterations=1)
    out = img.copy()
    out[mask > 0] = (236, 236, 230)
    return out


def _deskew_ledger(img: np.ndarray) -> np.ndarray:
    """Rotate slightly tilted phone photos using near-horizontal ruling lines."""
    try:
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=max(80, w // 8),
            minLineLength=int(w * 0.35), maxLineGap=20,
        )
        if lines is None or len(lines) == 0:
            return img
        angles = []
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            if abs(int(x2) - int(x1)) < 8:
                continue
            ang = math.degrees(math.atan2(int(y2) - int(y1), int(x2) - int(x1)))
            if abs(ang) <= 8:
                angles.append(ang)
        if len(angles) < 4:
            return img
        angle = float(np.median(angles))
        if abs(angle) < 0.35:
            return img
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            img, matrix, (w, h), flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return img


def _normalize_lighting(img: np.ndarray) -> np.ndarray:
    """CLAHE on the L channel to flatten shadows from phone flash / angle."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l_ch = clahe.apply(l_ch)
    return cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)


def suppress_grid_lines(img: np.ndarray) -> np.ndarray:
    """Paint printed ledger rules paper-white so they do not split handwritten strokes."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape[:2]
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 8
    )
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 18, 20), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 22, 16)))
    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=1)
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel, iterations=1)
    lines = cv2.bitwise_or(h_lines, v_lines)
    if len(img.shape) == 3:
        out = img.copy()
        out[lines > 0] = (245, 245, 240)
        return out
    out = gray.copy()
    out[lines > 0] = 255
    return out


def preprocess_ledger_image(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return (working_bgr, ocr_bgr).
    working_bgr is deskewed / lit / highlighter-cleaned (used for crops).
    ocr_bgr is the same with printed grid suppressed (used for full-page OCR).
    """
    if img is None or img.size == 0:
        return img, img
    try:
        work = _deskew_ledger(img)
        work = _neutralize_highlighter(work)
        work = _normalize_lighting(work)
        ocr_img = suppress_grid_lines(work)
        return work, ocr_img
    except Exception as exc:
        logger.warning("Ledger preprocess failed: %s", exc)
        return img, img


def _encode_jpg(img: np.ndarray, quality: int = 90) -> bytes:
    if img is None or img.size == 0:
        raise ValueError("No image to encode")
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok or buf is None:
        raise ValueError("JPEG encode failed")
    return buf.tobytes()


def _data_url_jpeg(raw: bytes) -> str:
    if not raw:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("utf-8")


def _bgr_to_rgb(img: np.ndarray) -> np.ndarray:
    if img is None or img.size == 0:
        return img
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _upscale_for_ocr(crop: np.ndarray, min_height: int = 72, scale: int = 3) -> np.ndarray:
    if crop is None or crop.size == 0:
        return crop
    h, w = crop.shape[:2]
    factor = max(scale, int(math.ceil(min_height / float(max(h, 1)))))
    factor = min(factor, 5)
    if factor <= 1:
        return crop
    interp = cv2.INTER_CUBIC if factor >= 2 else cv2.INTER_LINEAR
    return cv2.resize(crop, (max(8, w * factor), max(8, h * factor)), interpolation=interp)


def _pad_white(crop: np.ndarray, px: int = 12) -> np.ndarray:
    if crop is None or crop.size == 0:
        return crop
    color = (255, 255, 255) if len(crop.shape) == 3 else 255
    return cv2.copyMakeBorder(crop, px, px, px, px, cv2.BORDER_CONSTANT, value=color)


# ===========================================================================
# Full-page OCR
# ===========================================================================

def _tokens_from_easyocr(results) -> List[Dict[str, Any]]:
    tokens: List[Dict[str, Any]] = []
    for item in results or []:
        if not item or len(item) < 2:
            continue
        polygon = item[0]
        text = str(item[1]).strip()
        conf = float(item[2]) if len(item) >= 3 else 0.85
        if not text:
            continue
        xs = [float(pt[0]) for pt in polygon]
        ys = [float(pt[1]) for pt in polygon]
        tokens.append({
            "text": text, "confidence": round(conf, 2),
            "x_left": round(min(xs), 1), "x_right": round(max(xs), 1),
            "y_top": round(min(ys), 1), "y_bottom": round(max(ys), 1),
            "y_center": round(sum(ys) / len(ys), 1),
            "bbox": [round(min(xs), 1), round(min(ys), 1),
                     round(max(xs), 1), round(max(ys), 1)],
        })
    return tokens


def _easyocr_read(reader, img, allowlist: Optional[str] = None) -> List[Dict[str, Any]]:
    """Run EasyOCR on a BGR/gray numpy image with ledger-tuned detector settings."""
    if reader is None or img is None or img.size == 0:
        return []
    # EasyOCR treats 3-channel numpy as BGR (OpenCV). Do not convert to RGB.
    kwargs = dict(
        detail=1,
        paragraph=False,
        decoder="greedy",
        mag_ratio=1.0,
        canvas_size=1600,
        min_size=10,
    )
    if allowlist:
        kwargs["allowlist"] = allowlist
    try:
        return _tokens_from_easyocr(reader.readtext(img, **kwargs))
    except TypeError:
        slim = {"detail": 1, "paragraph": False}
        if allowlist:
            slim["allowlist"] = allowlist
        try:
            return _tokens_from_easyocr(reader.readtext(img, **slim))
        except Exception as exc:
            logger.warning("EasyOCR read error: %s", exc)
            return []
    except Exception as exc:
        logger.warning("EasyOCR read error: %s", exc)
        return []


def run_full_page_ocr(
    image_bytes: bytes, img: Optional[np.ndarray] = None
) -> List[Dict[str, Any]]:
    """
    Single EasyOCR pass on the whole page.
    Returns flat list of spatial token dicts with x_left/right, y_top/bottom/center.
    Falls back to pytesseract if EasyOCR is unavailable.
    """
    tokens: List[Dict[str, Any]] = []
    reader = _get_reader()

    page = img
    if page is None and image_bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        page = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if reader is not None and page is not None:
        tokens = _easyocr_read(reader, page)

    if not tokens and image_bytes:
        try:
            import pytesseract
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            data = pytesseract.image_to_data(pil_img, config="--psm 6", output_type=pytesseract.Output.DICT)
            n = len(data.get("text", []))
            for i in range(n):
                text = str(data["text"][i]).strip()
                if not text:
                    continue
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                conf_raw = data["conf"][i]
                try:
                    conf = max(0.0, float(conf_raw) / 100.0) if float(conf_raw) >= 0 else 0.55
                except Exception:
                    conf = 0.55
                tokens.append({
                    "text": text, "confidence": round(conf, 2),
                    "x_left": float(x), "x_right": float(x + w),
                    "y_top": float(y), "y_bottom": float(y + h),
                    "y_center": float(y + h / 2.0),
                    "bbox": [float(x), float(y), float(x + w), float(y + h)],
                })
            if not tokens:
                txt = pytesseract.image_to_string(pil_img, config="--psm 6")
                for i, line in enumerate(txt.splitlines()):
                    line = line.strip()
                    if line:
                        y0 = float(i * 35)
                        tokens.append({
                            "text": line, "confidence": 0.70,
                            "x_left": 10.0, "x_right": float(pil_img.width - 10),
                            "y_top": y0, "y_bottom": y0 + 28.0, "y_center": y0 + 14.0,
                            "bbox": [10.0, y0, float(pil_img.width - 10), y0 + 28.0],
                        })
        except Exception:
            pass

    return tokens


def extract_raw_ocr_response(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Legacy alias."""
    return run_full_page_ocr(image_bytes)


# ===========================================================================
# Column boundary detection
# ===========================================================================

def _looks_like_amount_text(text: str) -> bool:
    val, _, status = _clean_number(text)
    return status in ("VALID", "AMBIGUOUS_DECIMAL") and val is not None


def _detect_vertical_rule_xs(img: np.ndarray) -> List[int]:
    """X positions of printed vertical ledger rules."""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        h, w = gray.shape[:2]
        bw = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 8
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 18, 20)))
        vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)
        col_sum = np.sum(vert > 0, axis=0).astype(np.float32)
        thresh = max(h * 0.28, float(np.percentile(col_sum, 92)))
        xs = []
        in_run, run_start = False, 0
        for x, v in enumerate(col_sum):
            if v >= thresh:
                if not in_run:
                    in_run, run_start = True, x
            elif in_run:
                xs.append((run_start + x) // 2)
                in_run = False
        if in_run:
            xs.append((run_start + w) // 2)
        merged: List[int] = []
        for x in xs:
            if not merged or x - merged[-1] > w * 0.04:
                merged.append(int(x))
        return merged
    except Exception:
        return []


def detect_column_bounds(
    img: np.ndarray, tokens: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Pixel X-boundaries for each column.  Defaults skip the Folio column.
    Refined from printed vertical rules, header tokens, and amount-number clusters.
    """
    h, w = img.shape[:2]
    bounds = {
        "p_start":         int(0.08 * w),
        "p_end":           int(0.62 * w),
        "amt_rs_start":    int(0.72 * w),
        "amt_rs_end":      int(0.90 * w),
        "amt_paise_end":   int(0.97 * w),
        "amt_paise_start": int(0.90 * w),
    }

    rules = _detect_vertical_rule_xs(img)
    if len(rules) >= 3:
        interior = [x for x in rules if 0.05 * w < x < 0.97 * w]
        if len(interior) >= 3:
            interior = sorted(interior)
            bounds["p_start"] = max(bounds["p_start"], interior[0])
            bounds["amt_paise_end"] = min(bounds["amt_paise_end"], interior[-1] + 4)
            bounds["amt_rs_end"] = interior[-1] if len(interior) >= 4 else int(0.90 * w)
            bounds["amt_rs_start"] = interior[-2] if len(interior) >= 4 else interior[-1]
            folio_candidates = [x for x in interior if x < bounds["amt_rs_start"] - 8]
            if folio_candidates:
                bounds["p_end"] = folio_candidates[-1]
            bounds["amt_paise_start"] = bounds["amt_rs_end"]

    for tok in tokens:
        txt = tok["text"].lower()
        xl, xr = tok["x_left"], tok["x_right"]
        if any(kw in txt for kw in ("amount", "rupe", " rs", "rs.", "रकम")) and xl > 0.50 * w:
            bounds["amt_rs_start"] = max(int(0.62 * w), min(bounds["amt_rs_start"], int(xl)))
            bounds["p_end"] = min(bounds["p_end"], bounds["amt_rs_start"] - 8)
        elif any(kw in txt for kw in ("folio", "l.f", " pg", "pg.", "पृष्ठ")) and xl > 0.45 * w:
            bounds["p_end"] = min(bounds["p_end"], int(xl - 4))
            bounds["amt_rs_start"] = max(bounds["amt_rs_start"], int(xr + 4))

    amt_lefts = []
    for t in tokens:
        if t["x_left"] <= 0.55 * w:
            continue
        val, _, st = _clean_number(t["text"])
        if st == "VALID" and val is not None and val >= 100:
            amt_lefts.append(t["x_left"])
    if len(amt_lefts) >= 3:
        cluster_start = int(np.percentile(amt_lefts, 12))
        bounds["amt_rs_start"] = min(bounds["amt_rs_start"], max(int(0.62 * w), cluster_start - 6))
        if bounds["p_end"] > bounds["amt_rs_start"] - 6:
            bounds["p_end"] = bounds["amt_rs_start"] - 10

    bounds["amt_rs_end"] = max(bounds["amt_rs_start"] + 20, min(bounds["amt_rs_end"], int(0.93 * w)))
    bounds["amt_paise_start"] = bounds["amt_rs_end"]
    bounds["amt_paise_end"] = max(bounds["amt_rs_end"] + 8, int(0.97 * w))
    bounds["p_end"] = max(int(0.40 * w), min(bounds["p_end"], bounds["amt_rs_start"] - 6))
    return bounds


def detect_table_column_boundaries(
    img: np.ndarray, raw_tokens: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Legacy alias."""
    return detect_column_bounds(img, raw_tokens)


# ===========================================================================
# Row grouping
# ===========================================================================

_PRINTED_HEADER_RE = re.compile(
    r"^(date|particulars|folio|amount|receipts|payments|day\s*book|"
    r"page|rupees?|paise|p\.?)$",
    re.I,
)


def _is_printed_header_token(tok: Dict[str, Any], img_h: float) -> bool:
    txt = re.sub(r"[^a-zA-Z\s.]", "", tok.get("text", "")).strip()
    if not txt:
        return False
    if _PRINTED_HEADER_RE.match(txt.lower()) and tok["y_top"] < img_h * 0.14:
        return True
    return False


def _split_group_on_amounts(
    group: List[Dict[str, Any]], img_w: float, median_h: float
) -> List[List[Dict[str, Any]]]:
    """If a cluster contains two amount-column numbers, it is two ledger rows."""
    amt_toks = [
        t for t in group
        if _looks_like_amount_text(t["text"]) and t["x_left"] > img_w * 0.50
    ]
    if len(amt_toks) < 2:
        return [group]
    amt_toks = sorted(amt_toks, key=lambda t: t["y_center"])
    split_ys = []
    for a, b in zip(amt_toks, amt_toks[1:]):
        if abs(b["y_center"] - a["y_center"]) >= max(10.0, median_h * 0.45):
            split_ys.append((a["y_center"] + b["y_center"]) / 2.0)
    if not split_ys:
        return [group]
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(len(split_ys) + 1)]
    for tok in group:
        idx = 0
        while idx < len(split_ys) and tok["y_center"] > split_ys[idx]:
            idx += 1
        buckets[idx].append(tok)
    return [b for b in buckets if b]


def group_tokens_into_rows(
    tokens: List[Dict[str, Any]], img_h: float, img_w: float = 1000.0
) -> List[List[Dict[str, Any]]]:
    """Cluster tokens sharing the same Y-position into row groups."""
    content = [t for t in tokens if not _is_printed_header_token(t, img_h)] or tokens
    if not content:
        return []
    sorted_tokens = sorted(content, key=lambda t: t["y_center"])
    heights = [t["y_bottom"] - t["y_top"] for t in sorted_tokens if t["y_bottom"] > t["y_top"]]
    median_h = float(np.median(heights)) if heights else 25.0
    # Tight band so long descenders (g/y/f) do not glue the next printed row.
    tolerance = max(12.0, min(36.0, median_h * 0.55))

    groups: List[List[Dict]] = []
    current = [sorted_tokens[0]]
    for tok in sorted_tokens[1:]:
        gy = sum(t["y_center"] for t in current) / len(current)
        if abs(tok["y_center"] - gy) <= tolerance:
            current.append(tok)
        else:
            groups.append(current)
            current = [tok]
    if current:
        groups.append(current)

    split: List[List[Dict]] = []
    for g in groups:
        split.extend(_split_group_on_amounts(g, img_w, median_h))
    return split[:50]


# ===========================================================================
# Number cleaning
# ===========================================================================

def _clean_number(text: str) -> Tuple[Optional[float], str, str]:
    """
    Convert raw OCR text to float.
    Returns (value, cleaned_str, status).
    Status: VALID | EMPTY | NO_DIGITS | AMBIGUOUS_DECIMAL | INVALID_FORMAT
    """
    if not text:
        return None, "", "EMPTY"
    t = re.sub(r"[Rrs\u20b9=]", "", str(text)).strip()
    SUBS = {"S": "5", "s": "5", "O": "0", "o": "0", "Q": "0",
            "I": "1", "l": "1", "i": "1", "|": "1", "B": "8", "Z": "2", "z": "2"}
    cleaned = ""
    for ch in t:
        if ch.isdigit() or ch in ".,":
            cleaned += ch
        elif ch in SUBS:
            cleaned += SUBS[ch]
    no_comma = cleaned.replace(",", "").strip(" .")
    if not any(c.isdigit() for c in no_comma):
        return None, t, "NO_DIGITS"
    # Drop a trailing separator left by paise-column noise: "16123."
    no_comma = no_comma.strip(".")
    if re.match(r"^\d+(\.\d+)?$", no_comma):
        val = float(no_comma)
        if val > 100_000 and "." not in no_comma:
            return None, no_comma, "AMBIGUOUS_DECIMAL"
        return val, no_comma, "VALID"
    return None, no_comma, "INVALID_FORMAT"


def clean_ocr_number(t_in: str) -> Tuple[Optional[float], str, str]:
    """Legacy alias."""
    return _clean_number(t_in)


# ===========================================================================
# Amount cell: 2-pass OCR on isolated crop
# ===========================================================================

def _remove_lines_from_gray(gray: np.ndarray) -> np.ndarray:
    """Remove rules that span most of the crop; leave handwritten strokes."""
    h, w = gray.shape[:2]
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 8
    )
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(int(w * 0.70), 16), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(int(h * 0.70), 14)))
    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel)
    out = gray.copy()
    out[h_lines > 0] = 255
    out[v_lines > 0] = 255
    return out


def _is_paise_leak_pair(shorter: float, longer: float) -> bool:
    """True when `longer` is `shorter` with 1–2 extra trailing digits (paise/folio leak)."""
    if shorter is None or longer is None:
        return False
    if shorter <= 0 or longer <= shorter:
        return False
    s, l = str(int(round(shorter))), str(int(round(longer)))
    if not l.startswith(s) or len(l) <= len(s):
        return False
    extra = l[len(s):]
    return 1 <= len(extra) <= 2


def _read_digits_from_crop(reader, crop: np.ndarray) -> Tuple[str, float]:
    if crop is None or crop.size == 0 or reader is None:
        return "", 0.0
    prepared = _pad_white(_upscale_for_ocr(crop))
    tokens = _easyocr_read(reader, prepared, allowlist="0123456789.,- ")
    if not tokens:
        try:
            res = reader.readtext(prepared, allowlist="0123456789.,- ")
            tokens = _tokens_from_easyocr(res)
        except Exception:
            return "", 0.0
    if not tokens:
        return "", 0.0
    txt = " ".join(t["text"] for t in tokens).strip()
    conf = float(np.mean([t["confidence"] for t in tokens]))
    return txt, conf


def _rupee_score(val: float) -> float:
    """Prefer real rupee figures over folio/paise fragments (1, 0, 5, 13)."""
    if val is None:
        return -1.0
    if val == 0:
        return 15.0
    digits = len(str(int(round(abs(val)))))
    if digits >= 6:
        return 20.0
    if digits == 5:
        return 120.0
    if digits == 4:
        return 100.0
    if digits == 3:
        return 70.0
    if digits == 2:
        return 20.0
    return 5.0


def _merge_amount_tokens(
    group: List[Dict[str, Any]], amt_rs_start: int, amt_paise_start: int
) -> List[Dict[str, Any]]:
    """Join split amount digits in the rupee column, e.g. 12 + 000 -> 12000."""
    digit_toks = []
    for tok in group:
        if tok["x_left"] < amt_rs_start - 4:
            continue
        if tok["x_left"] >= amt_paise_start:
            val, _, st = _clean_number(tok["text"])
            if st == "VALID" and val is not None and val < 100:
                continue
        digits = re.sub(r"[^\d]", "", tok["text"] or "")
        if not digits:
            continue
        digit_toks.append({
            "digits": digits,
            "x_left": tok["x_left"],
            "x_right": tok["x_right"],
            "confidence": tok.get("confidence", 0.8),
        })
    digit_toks.sort(key=lambda t: t["x_left"])
    merged: List[Dict[str, Any]] = []
    i = 0
    while i < len(digit_toks):
        acc = digit_toks[i]["digits"]
        x0 = digit_toks[i]["x_left"]
        x1 = digit_toks[i]["x_right"]
        conf = digit_toks[i]["confidence"]
        j = i + 1
        while j < len(digit_toks):
            gap = digit_toks[j]["x_left"] - x1
            nxt = acc + digit_toks[j]["digits"]
            if gap > 22 or len(nxt) > 6:
                break
            acc = nxt
            x1 = digit_toks[j]["x_right"]
            conf = min(conf, digit_toks[j]["confidence"])
            j += 1
        val, raw, st = _clean_number(acc)
        if st == "VALID" and val is not None:
            merged.append({
                "amount": val, "amount_raw": raw,
                "confidence": conf, "x_left": x0,
            })
            i = j
            continue
        val, raw, st = _clean_number(digit_toks[i]["digits"])
        if st == "VALID" and val is not None:
            merged.append({
                "amount": val, "amount_raw": raw,
                "confidence": digit_toks[i]["confidence"],
                "x_left": digit_toks[i]["x_left"],
            })
        i += 1
    return merged


def amount_from_row_tokens(
    group: List[Dict[str, Any]],
    amt_rs_start: int,
    amt_paise_start: int,
) -> Optional[Dict[str, Any]]:
    """Best rupee amount already recognised in the full-page scan for this row."""
    cands = _merge_amount_tokens(group, amt_rs_start, amt_paise_start)
    if not cands:
        return None
    vals = [c["amount"] for c in cands]
    cands = [
        c for c in cands
        if not any(_is_paise_leak_pair(other, c["amount"]) for other in vals if other != c["amount"])
    ] or cands
    best = max(cands, key=lambda c: (_rupee_score(c["amount"]), c["amount"], c["confidence"]))
    return {
        "amount": best["amount"],
        "amount_raw": best["amount_raw"],
        "confidence": best["confidence"],
        "all_cands": cands,
    }


def extract_amount_from_crop(
    crop_rs: np.ndarray, crop_full: np.ndarray,
    page_hint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Multi-pass numeric OCR on the Amount Rupees column crop.
      Pass 0: full-page token already sitting in this row's amount column
      Pass 1: upscaled raw crop (digits allowlist)
      Pass 2: CLAHE + bilateral + line removal
      Pass 3: Otsu binary
    Extra trailing digits from the paise/folio column are rejected.
    """
    reader = _get_reader()
    crop_b64 = ""
    empty = {
        "amount": None, "amount_raw": "", "amount_status": "NOT_DETECTED",
        "candidates": [], "multi_pass_agreement": 0.0,
        "numeric_validation_score": 0.0, "ocr_confidence": 0.0,
        "why_selected": "No crop available", "amount_crop_b64": "",
    }
    # Fast path only for a real rupee figure. Tiny tokens (0, 1, 5, 13) are folio/paise.
    hint_val = page_hint.get("amount") if page_hint else None
    if hint_val is not None and hint_val >= 100:
        return {
            "amount": page_hint["amount"],
            "amount_raw": page_hint.get("amount_raw", ""),
            "amount_status": "CONFIRMED",
            "candidates": [{"pass": "Pass0(PageToken)", "ocr_text": page_hint.get("amount_raw", ""),
                            "value": page_hint["amount"], "status": "VALID",
                            "confidence": page_hint.get("confidence", 0.8)}],
            "multi_pass_agreement": 1.0, "numeric_validation_score": 90.0,
            "ocr_confidence": page_hint.get("confidence", 0.8),
            "why_selected": "Full-page amount token",
            "amount_crop_b64": "",
        }

    candidates = []
    txt1, decimal_val = "", None

    if page_hint and page_hint.get("amount") is not None:
        candidates.append({
            "pass": "Pass0(PageToken)",
            "ocr_text": str(page_hint.get("amount_raw") or page_hint["amount"]),
            "value": page_hint["amount"], "status": "VALID",
            "confidence": float(page_hint.get("confidence") or 0.8),
        })

    # Pass 1: upscaled raw crop
    try:
        txt1, conf1 = _read_digits_from_crop(reader, crop_rs)
        val1, clean1, st1 = _clean_number(txt1)
        if clean1:
            candidates.append({"pass": "Pass1(Raw)", "ocr_text": clean1,
                                "value": val1, "status": st1, "confidence": conf1})
        if txt1:
            dm = re.search(r"(\d+)[.\s]+(\d{2})$", txt1)
            if dm:
                mp, pp = dm.groups()
                if 0 < int(pp) < 100:
                    decimal_val = float(f"{mp}.{pp}")
                    candidates.append({"pass": "Pass1(Decimal)", "ocr_text": f"{mp}.{pp}",
                                       "value": decimal_val, "status": "VALID", "confidence": 0.90})
    except Exception:
        pass

    skip_extra = False
    if page_hint and page_hint.get("amount") is not None:
        p1_val = next((c["value"] for c in candidates if c["pass"] == "Pass1(Raw)" and c["value"] is not None), None)
        if p1_val is not None and p1_val == page_hint["amount"]:
            skip_extra = True

    # Pass 2 + 3 only when the page token and crop disagree (saves a lot of time)
    if not skip_extra:
        try:
            gray = cv2.cvtColor(crop_rs, cv2.COLOR_BGR2GRAY) if len(crop_rs.shape) == 3 else crop_rs
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = _remove_lines_from_gray(clahe.apply(gray))
            filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
            txt2, conf2 = _read_digits_from_crop(reader, filtered)
            val2, clean2, st2 = _clean_number(txt2)
            if clean2:
                candidates.append({"pass": "Pass2(CLAHE)", "ocr_text": clean2,
                                    "value": val2, "status": st2, "confidence": conf2})
            if decimal_val is None and txt2:
                dm2 = re.search(r"(\d+)[.\s]+(\d{2})$", txt2)
                if dm2:
                    mp, pp = dm2.groups()
                    if 0 < int(pp) < 100:
                        decimal_val = float(f"{mp}.{pp}")
                        candidates.append({"pass": "Pass2(Decimal)", "ocr_text": f"{mp}.{pp}",
                                           "value": decimal_val, "status": "VALID", "confidence": 0.90})
        except Exception:
            pass

        try:
            gray = cv2.cvtColor(crop_rs, cv2.COLOR_BGR2GRAY) if len(crop_rs.shape) == 3 else crop_rs
            clean_g = _remove_lines_from_gray(gray)
            _, bw = cv2.threshold(clean_g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if float(np.mean(bw)) < 127:
                bw = 255 - bw
            txt3, conf3 = _read_digits_from_crop(reader, bw)
            val3, clean3, st3 = _clean_number(txt3)
            if clean3:
                candidates.append({"pass": "Pass3(Binary)", "ocr_text": clean3,
                                    "value": val3, "status": st3, "confidence": conf3})
        except Exception:
            pass

    valid = [c for c in candidates if c["value"] is not None]
    if not valid:
        return {**empty, "amount_raw": txt1, "candidates": candidates,
                "why_selected": "No digits in crop", "amount_crop_b64": crop_b64}

    # Drop values that are a 1-digit paise leak of a shorter candidate.
    values = [c["value"] for c in valid]
    filtered_valid = []
    for c in valid:
        if any(_is_paise_leak_pair(other, c["value"]) for other in values if other != c["value"]):
            continue
        filtered_valid.append(c)
    if filtered_valid:
        valid = filtered_valid

    if decimal_val is not None and any(abs(c["value"] - decimal_val) < 0.001 for c in valid):
        selected, raw = decimal_val, f"{decimal_val:.2f}"
        agreement, v_score, status = 0.85, 90.0, "CONFIRMED"
        why = f"Decimal paise: Rs.{decimal_val:.2f}"
    else:
        cnt = Counter(c["value"] for c in valid)
        selected = max(cnt.keys(), key=lambda v: (_rupee_score(v), v))
        freq = cnt[selected]
        agreement = freq / float(len(valid))
        raw = next(c["ocr_text"] for c in valid if c["value"] == selected)
        v_score = min(100.0, 35.0 + 40.0 * agreement + 25.0)
        if agreement >= 0.50 and v_score >= 80.0:
            status = "CONFIRMED"
            why = f"{freq}/{len(valid)} passes agree Rs.{selected:,.0f}"
        else:
            status = "REVIEW_REQUIRED"
            why = f"Passes disagree: {', '.join(str(v) for v in cnt)}"

    avg_conf = float(np.mean([c["confidence"] for c in valid]))
    return {
        "amount": selected, "amount_raw": raw, "amount_status": status,
        "candidates": candidates, "multi_pass_agreement": round(agreement, 2),
        "numeric_validation_score": round(v_score, 1), "ocr_confidence": round(avg_conf, 2),
        "why_selected": why, "amount_crop_b64": crop_b64,
    }


def analyze_amount_cell(crop_rs, crop_paise, crop_full):
    """Legacy 3-arg alias -> calls 2-pass version."""
    return extract_amount_from_crop(crop_rs, crop_full)


# ===========================================================================
# Description classification
# ===========================================================================

# OPENING_CASH must be listed before CASH_SALE so "opening cash" never
# gets stolen by the shorter "cash" alias.
_CATEGORY_ALIASES: Dict[str, List[str]] = {
    "OPENING_CASH": [
        "opening balance", "opening bal", "opening cash", "opening b",
        "op bal", "op.bal", "opn bal", "open bal", "open b",
        "opening", "opning", "openin", "openi", "openg b", "openning", "opn",
        "ofenir", "opeming", "opeing",
    ],
    "CASH_SALE": [
        "cash sale", "cash sales", "cash payment", "cash/sale", "cash/s", "cash s",
        "cashsale", "cah sale", "csh sale", "cash sal", "cash sl",
        "gash sale", "cash ale", "cosh sale", "oash sale", "casn sale",
    ],
    "CARD_QR_PAYTM": [
        "credit card", "credit card sale", "card sale", "crdit card",
        "credt card", "credir card", "credit car", "creait card",
        "creidit", "creditcard", "card qr", "cardqr",
        "pattm", "phaytm", "payt", "pay tm",
        "debit card", "debit", "credit", "card", "paytm", "upi", "qr",
    ],
    "ZOMATO": [
        "zomato", "zomato online", "zomato sale", "zom",
        "20m", "20mato", "zomto", "zomatu", "zomat",
        "zomaro", "zomoto", "zomatoo", "z0mato", "zmat", "zmato",
    ],
    "SWIGGY": [
        "swiggy", "swiggy sale", "swigy", "subggy", "swig",
        "swigyy", "swigg", "swiggu", "swgy", "swigqy", "swingy",
    ],
    "DINEOUT": [
        "dineout", "dine out", "dine-out", "dine",
        "dineou", "dinout", "din out", "dineot",
        "di neou", "pi neou", "dine ou", "dineont",
        "dinaout", "dneout", "di nout", "d1neout", "pineoyt", "pineout",
    ],
    "SALARY_ADVANCE": [
        "salary advance", "salary adv", "boys advance", "advance guard",
        "advance salary", "guard advance", "salary advnce", "salary advanc",
        "salry advance", "sal adv", "sal advance", "slry advance", "adv salary",
        "salary", "advance",
    ],
    "SERVICE_CHARGE": [
        "service charge", "service ch", "serv charge", "s.c", "sc",
        "s c", "ser charge", "srv charge",
    ],
}

_TOTAL_KWS = frozenset({
    "total sale", "today sale", "gross sale",
    "total sales", "today sales", "todays sale", "today's sale",
    "todaysale", "totalsale",
})
_EXPENSE_MARKERS = ("#", "*")
_BALANCE_ONLY_RE = re.compile(
    r"^(total|totl|balance|bal|closing|cd|c/d|b/f|c/f|-|—|–)?$",
    re.I,
)


def classify_description(description_raw: str) -> Tuple[str, float]:
    """
    Map a handwritten row description to an accounting category.
    Returns (category, confidence).

    Priority order:
      1. Expense markers (#, *) or (e)/exp keywords  -> SITE_EXPENSE
         (unless salary/advance also present)
      2. 'opening' keyword fast-exit                  -> OPENING_CASH
      3. Total / summary rows                         -> TODAY_SALE
      4. Service charge (sc)                          -> SERVICE_CHARGE
      5. Alias exact, word, substring, fuzzy          -> best match
    """
    if not description_raw:
        return "UNKNOWN", 0.0

    raw = str(description_raw)
    raw_l = raw.lower()
    norm = re.sub(r"[^a-z0-9\s]", "", raw_l).strip()

    # Expense indicator — hash may not be at index 0 if a date token precedes it.
    is_exp = (
        any(raw.strip().startswith(m) for m in _EXPENSE_MARKERS)
        or bool(re.search(r"(^|\s)[#*](?=\s|[A-Za-z])", raw))
        or bool(re.search(r"\(\s*e\s*\)", raw_l))
    )
    has_exp_kw = any(kw in norm.split() for kw in ("exp", "expense"))
    if is_exp or has_exp_kw:
        if "salary" not in norm and "advance" not in norm:
            return "SITE_EXPENSE", 0.90

    # Opening balance fast-exit
    if "opening" in norm or "op bal" in norm or "opn bal" in norm:
        return "OPENING_CASH", 0.92

    # Total/summary rows — used as a checksum, not a sales channel
    if any(kw in norm for kw in _TOTAL_KWS):
        return "TODAY_SALE", 0.90

    # Service charge is recorded on the register but is not a sales channel
    if norm in ("sc", "s c") or "service charge" in norm or re.fullmatch(r"s\.?c\.?", raw_l.strip()):
        return "SERVICE_CHARGE", 0.88

    # Alias matching — short aliases must be whole words to avoid false hits
    best_cat, best_score = "UNKNOWN", 0.0
    for cat, aliases in _CATEGORY_ALIASES.items():
        for alias in aliases:
            if alias == norm:
                return cat, 0.98
            if len(alias) <= 3:
                if re.search(r"(^|\s)" + re.escape(alias) + r"(\s|$)", norm):
                    score = 0.86
                    if score > best_score:
                        best_cat, best_score = cat, score
                continue
            if alias in norm:
                score = (0.92 if len(alias) >= 6 else
                         0.82 if len(alias) >= 5 else
                         0.70 if len(alias) >= 4 else 0.50)
                if score > best_score:
                    best_cat, best_score = cat, score
            elif norm and len(norm) >= 4 and norm in alias:
                if 0.65 > best_score:
                    best_cat, best_score = cat, 0.65
            elif len(alias) >= 4 and len(norm) >= 4:
                ratio = difflib.SequenceMatcher(None, alias, norm).ratio()
                if ratio >= 0.62 and ratio > best_score:
                    best_cat, best_score = cat, round(ratio, 2)

    return best_cat, best_score


def classify_row_description(description_raw: str) -> Tuple[str, float]:
    """Legacy alias used by tests and reprocess-row endpoint."""
    return classify_description(description_raw)


# ===========================================================================
# Field mapping
# ===========================================================================

_FIELD_KEY_MAP = {
    "OPENING_CASH":   "opening_balance",
    "CASH_SALE":      "cash",
    "CARD_QR_PAYTM":  "card_qr",
    "ZOMATO":         "zomato",
    "SWIGGY":         "swiggy",
    "DINEOUT":        "dineout",
    "SALARY_ADVANCE": "salary_advance",
}

_EMPTY_FIELD: Dict[str, Any] = {
    "value": None, "confidence": 0.0, "ocr_confidence": 0.0,
    "numeric_validation_score": 0.0, "description_confidence": 0.0,
    "amount_confidence": 0.0, "classification_confidence": 0.0,
    "status": "NOT_DETECTED", "source_row_id": None, "source_row": "",
    "source_description": "", "raw_description": "", "amount_raw": "",
    "amount_crop_b64": "", "why_selected": "Not detected in register image",
    "candidates": [],
}


_DATE_PATTERN = re.compile(r"(\d{1,2})\s*[/.\-_]\s*(\d{1,2})\s*[/.\-_]\s*(\d{2,4})")

_SALES_TEMPLATE = [
    "OPENING_CASH",
    "TODAY_SALE",
    "CASH_SALE",
    "CARD_QR_PAYTM",  # Credit Card
    "CARD_QR_PAYTM",  # Paytm
    "SWIGGY",
    "ZOMATO",
    "DINEOUT",
    "SERVICE_CHARGE",
]


def _looks_like_balance_row(description_raw: str) -> bool:
    norm = re.sub(r"[^a-z0-9\s]", "", str(description_raw or "").lower()).strip()
    compact = re.sub(r"\s+", "", norm)
    if compact in ("", "-", "total", "totl", "balance", "bal", "closing", "cd", "cfd", "bf"):
        return True
    if len(compact) <= 1:
        return True
    if _BALANCE_ONLY_RE.match(norm or ""):
        return True
    return False


def _is_date_only_row(description_raw: str) -> bool:
    raw = str(description_raw or "").strip()
    if _DATE_PATTERN.fullmatch(raw.replace(" ", "")):
        return True
    if _DATE_PATTERN.fullmatch(raw):
        return True
    # OCR often reads 03/04/26 as "03 04 26" or with junk around it
    if _DATE_PATTERN.search(raw) and len(re.sub(r"[^a-zA-Z]", "", raw)) < 3:
        return True
    return False


def _apply_daybook_template(
    rows: List[Dict[str, Any]], cats: List[Tuple[str, float]]
) -> List[Tuple[str, float]]:
    """
    These day books always list sales in a fixed order. Align from Opening
    or Today Sale so a date row above them does not shift every field.
    """
    if len(rows) < 5:
        return cats
    cats = list(cats)
    first_exp = next(
        (i for i, (c, _) in enumerate(cats)
         if c in ("SITE_EXPENSE", "SALARY_ADVANCE")),
        len(rows),
    )

    sales_idx = [
        i for i in range(first_exp)
        if not _is_date_only_row(rows[i].get("description_raw", ""))
        and not _looks_like_balance_row(rows[i].get("description_raw", ""))
        and (rows[i].get("amount") is not None or rows[i].get("description_raw"))
    ]
    if len(sales_idx) < 6:
        return cats

    anchor_pos = 0
    anchor_row = None
    for i in sales_idx:
        if cats[i][0] == "TODAY_SALE":
            anchor_row, anchor_pos = i, 1
            break
    if anchor_row is None:
        for i in sales_idx:
            if cats[i][0] == "OPENING_CASH":
                anchor_row, anchor_pos = i, 0
                break
    if anchor_row is None:
        # First sales row with an amount is treated as opening
        for i in sales_idx:
            if rows[i].get("amount") is not None:
                anchor_row, anchor_pos = i, 0
                break
    if anchor_row is None:
        return cats

    try:
        start = sales_idx.index(anchor_row) - anchor_pos
    except ValueError:
        start = 0
    start = max(0, start)

    for pos, expected in enumerate(_SALES_TEMPLATE):
        si = start + pos
        if si >= len(sales_idx):
            break
        idx = sales_idx[si]
        cat, conf = cats[idx]
        if cat in ("SITE_EXPENSE", "SALARY_ADVANCE"):
            break
        if cat in ("UNKNOWN", expected) or conf < 0.85:
            cats[idx] = (expected, max(conf, 0.74))

    in_exp = False
    for i, (cat, conf) in enumerate(cats):
        if cat in ("SITE_EXPENSE", "SALARY_ADVANCE"):
            in_exp = True
            continue
        if i >= first_exp or in_exp:
            desc = rows[i].get("description_raw", "")
            if _looks_like_balance_row(desc):
                cats[i] = ("SKIP_TOTAL", 0.90)
            elif cat == "UNKNOWN":
                cats[i] = ("SITE_EXPENSE", 0.72)
            in_exp = True
    return cats


def _assign_field(fields, fkey, row, amt, amt_raw, desc_conf, amt_conf, v_score, cat_conf, why, crop_b64, cands, accumulate=False):
    amt_st = row.get("amount_status", "CONFIRMED")
    final_st = "CONFIRMED" if (amt_st == "CONFIRMED" and v_score >= 80.0) else "REVIEW_REQUIRED"
    oc = round(min(desc_conf, amt_conf if amt_conf > 0 else 0.80, cat_conf if cat_conf > 0 else 0.80), 2)
    src = f"Row #{row['row_id']} ({row['description_raw'][:20]})"
    payload = {
        "value": amt, "amount_raw": amt_raw,
        "confidence": oc, "ocr_confidence": amt_conf,
        "numeric_validation_score": v_score,
        "description_confidence": desc_conf, "amount_confidence": amt_conf,
        "classification_confidence": cat_conf, "status": final_st,
        "source_row_id": row["row_id"],
        "source_row": src,
        "source_description": row["description_raw"],
        "raw_description": row["description_raw"],
        "amount_crop_b64": crop_b64, "why_selected": why, "candidates": cands,
    }
    existing = fields.get(fkey) or dict(_EMPTY_FIELD)
    if existing.get("value") is None:
        fields[fkey] = payload
        return
    if accumulate and amt is not None:
        fields[fkey]["value"] = (existing["value"] or 0.0) + amt
        fields[fkey]["amount_raw"] = str(fields[fkey]["value"])
        fields[fkey]["source_description"] = (
            f"{existing.get('source_description', '')} + {row['description_raw']}"
        ).strip(" +")
        fields[fkey]["why_selected"] = (
            f"{existing.get('why_selected', '')}; plus Row #{row['row_id']}"
        )
        fields[fkey]["source_row"] = f"{existing.get('source_row', '')} + {src}"


def map_rows_to_fields(
    rows: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Classify each row description and assign to accounting field.
    Credit Card and Paytm are summed into card_qr.
    Expense subtotals / closing cash lines are skipped.
    Returns (fields_dict, itemized_expenses_list).
    """
    fields = {k: dict(_EMPTY_FIELD) for k in (
        "cash", "card_qr", "zomato", "swiggy", "dineout",
        "opening_balance", "site_expenses", "salary_advance",
    )}
    itemized: List[Dict] = []
    cats = [classify_description(row.get("description_raw", "")) for row in rows]
    cats = _apply_daybook_template(rows, cats)

    for row, (cat, cat_conf) in zip(rows, cats):
        amt       = row.get("amount")
        amt_raw   = row.get("amount_raw")
        desc_conf = row.get("description_confidence", 0.85)
        amt_conf  = row.get("amount_confidence", 0.85)
        v_score   = row.get("numeric_validation_score", 85.0)
        why       = row.get("why_selected", "")
        crop_b64  = row.get("amount_crop_b64", "")
        cands     = row.get("candidates", [])
        row["classification_confidence"] = cat_conf

        if cat in ("TODAY_SALE", "SERVICE_CHARGE", "SKIP_TOTAL"):
            row["status"] = f"SKIPPED_{cat}"
            continue

        if cat == "SITE_EXPENSE" or (
            cat == "UNKNOWN" and _looks_like_balance_row(row.get("description_raw", ""))
        ):
            if cat != "SITE_EXPENSE":
                row["status"] = "SKIPPED_TOTAL"
                continue
            if _looks_like_balance_row(row.get("description_raw", "")):
                row["status"] = "SKIPPED_TOTAL"
                continue
            if amt is not None and amt < 10:
                row["status"] = "SKIPPED_TINY_AMOUNT"
                continue
            if amt is not None or amt_raw:
                itemized.append({
                    "row_id": row["row_id"], "description": row["description_raw"],
                    "amount_raw": amt_raw, "amount": amt,
                    "amount_crop_b64": crop_b64, "why_selected": why,
                    "numeric_validation_score": v_score,
                    "status": row.get("amount_status", "CONFIRMED"),
                })
                row["status"] = "CLASSIFIED_SITE_EXPENSE"
            continue

        fkey = _FIELD_KEY_MAP.get(cat)
        if not fkey:
            row["status"] = "UNCLASSIFIED"
            continue

        row["status"] = f"CLASSIFIED_{fkey.upper()}"
        accumulate = fkey in ("card_qr", "salary_advance")
        if fkey in ("cash", "card_qr", "zomato", "swiggy", "dineout") and amt is not None and 0 < amt < 10:
            amt = None
        if amt is not None:
            _assign_field(
                fields, fkey, row, amt, amt_raw, desc_conf, amt_conf, v_score,
                cat_conf, why, crop_b64, cands, accumulate=accumulate,
            )
        elif amt_raw and fields[fkey]["value"] is None:
            fields[fkey] = {
                **dict(_EMPTY_FIELD), "value": None, "amount_raw": amt_raw,
                "confidence": 0.50, "ocr_confidence": 0.50,
                "numeric_validation_score": v_score,
                "description_confidence": desc_conf,
                "classification_confidence": cat_conf, "status": "REVIEW_REQUIRED",
                "source_row_id": row["row_id"],
                "source_row": f"Row #{row['row_id']} ({row['description_raw'][:20]})",
                "source_description": row["description_raw"],
                "raw_description": row["description_raw"],
                "amount_crop_b64": crop_b64, "why_selected": why, "candidates": cands,
            }

    if itemized:
        total = sum(i["amount"] for i in itemized if i["amount"] is not None)
        fields["site_expenses"] = {
            "value": total if total > 0 else None, "amount_raw": str(total),
            "confidence": 0.90, "ocr_confidence": 0.90,
            "numeric_validation_score": 92.0, "description_confidence": 0.90,
            "amount_confidence": 0.90, "classification_confidence": 0.90,
            "status": "CONFIRMED" if total > 0 else "NOT_DETECTED",
            "source_row_id": itemized[0]["row_id"],
            "source_row": f"Row #{itemized[0]['row_id']} ({len(itemized)} Expense Items)",
            "source_description": f"{len(itemized)} Expense Items",
            "raw_description": "Itemized Site Expenses",
            "amount_crop_b64": itemized[0].get("amount_crop_b64", ""),
            "why_selected": f"Sum of {len(itemized)} expense rows",
            "candidates": [], "items": itemized,
        }

    return fields, itemized


def classify_all_rows(rows, *args, **kwargs):
    """Legacy alias: delegates to map_rows_to_fields (returns fields, itemized tuple)."""
    return map_rows_to_fields(rows)



# ===========================================================================
# Helpers
# ===========================================================================

_DATE_PATTERN = re.compile(r"(\d{1,2})\s*[/.\-_]\s*(\d{1,2})\s*[/.\-_]\s*(\d{2,4})")


def _parse_date(d1: str, d2: str, d3: str) -> str:
    try:
        v1, v2, v3 = int(d1), int(d2), int(d3)
        year, month, day = 2026, 5, 2
        if   2024 <= v3 <= 2030: year = v3;        day, month = (v1, v2) if v2 <= 12 else (v2, v1)
        elif 24   <= v3 <= 30:   year = 2000 + v3; day, month = (v1, v2) if v2 <= 12 else (v2, v1)
        elif 2024 <= v1 <= 2030: year = v1;        day, month = (v3, v2) if v2 <= 12 else (v2, v3)
        elif 24   <= v1 <= 30:   year = 2000 + v1; day, month = (v3, v2) if v2 <= 12 else (v2, v3)
        elif 1 <= v2 <= 12 and 1 <= v1 <= 31: day, month = v1, v2
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d")


def parse_ocr_date(d1: str, d2: str, d3: str) -> str:
    """Legacy alias."""
    return _parse_date(d1, d2, d3)


def _sanitize(obj: Any) -> Any:
    """Recursively convert numpy types; replace NaN/Inf with 0.0 for JSON safety."""
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return 0.0 if (math.isnan(obj) or math.isinf(obj)) else float(obj)
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    return obj


def sanitize_json_obj(obj: Any) -> Any:
    """Legacy alias."""
    return _sanitize(obj)


def generate_image_previews(image_bytes: bytes) -> Tuple[str, str, str, float, float]:
    """Return (b64_original, b64_grayscale_norm, b64_amount_col, width, height) as raw JPEG base64."""
    if not image_bytes:
        return "", "", "", 1000.0, 1000.0
    try:
        img, _, _ = _decode_to_bgr(image_bytes)
        if img is None:
            return "", "", "", 1000.0, 1000.0
        h, w = img.shape[:2]
        b64_orig = base64.b64encode(_encode_jpg(img, 85)).decode("utf-8")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        b64_prep = base64.b64encode(_encode_jpg(cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR), 80)).decode("utf-8")
        x1 = int(0.52 * w)
        crop = img[:, x1:int(0.98 * w)]
        b64_crop = base64.b64encode(_encode_jpg(crop, 80)).decode("utf-8") if crop.size else b64_orig
        return b64_orig, b64_prep, b64_crop, float(w), float(h)
    except Exception:
        try:
            fallback = base64.b64encode(_encode_jpg(_decode_to_bgr(image_bytes)[0], 80)).decode("utf-8")
            return fallback, fallback, fallback, 1000.0, 1000.0
        except Exception:
            return "", "", "", 1000.0, 1000.0


def _annotate_row_boxes(image_bytes: bytes, rows: List[Dict[str, Any]]) -> str:
    """Draw bounding boxes on rows. Returns base64 JPEG string."""
    if not image_bytes or not rows:
        return ""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return ""
        h, w = img.shape[:2]
        for row in rows:
            bbox = row.get("row_bbox", [])
            if len(bbox) < 4:
                continue
            x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
            x2, y2 = min(w - 1, x2), min(h - 1, y2)
            color = (0, 200, 90) if row.get("amount") is not None else (240, 165, 0)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            label = f"#{row['row_id']} {row.get('description_raw','')[:16]}"
            if row.get("amount_raw"):
                label += f" => {row['amount_raw']}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            cv2.rectangle(img, (x1, max(0, y1 - th - 4)), (x1 + tw + 6, y1), color, -1)
            cv2.putText(img, label, (x1 + 3, max(th, y1 - 3)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)
        _, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception:
        return ""


def _print_diagnostic(rows: List[Dict], fields: Dict, expenses: List[Dict]) -> None:
    """ASCII-safe terminal diagnostic (Windows cp1252 compatible)."""
    try:
        print("=" * 60)
        print("REGISTER EXTRACTION DIAGNOSTIC")
        print(f"Rows: {len(rows)}  Expenses: {len(expenses)}")
        print("-" * 60)
        for r in rows:
            amt = r.get("amount_raw") or (str(r["amount"]) if r.get("amount") is not None else "-")
            print(f"  R{r['row_id']:2d}: {r.get('description_raw','')[:28]:30s}  Rs.{amt}")
        print("-" * 60)
        for label, key in [
            ("Opening Cash",  "opening_balance"),
            ("Cash Sale",     "cash"),
            ("Card / QR",     "card_qr"),
            ("Zomato",        "zomato"),
            ("Swiggy",        "swiggy"),
            ("Dineout",       "dineout"),
            ("Salary Advance","salary_advance"),
            ("Site Expenses", "site_expenses"),
        ]:
            f = fields.get(key, {})
            val = f"Rs.{f['value']:,.0f}" if f.get("value") is not None else "NOT DETECTED"
            src = f.get("source_row_id")
            print(f"  {label:20s} -> {val:18s}  (Row #{src or '-'})")
        print("=" * 60)
    except Exception:
        pass


# ===========================================================================
# Main entry point
# ===========================================================================

def parse_images_to_merged_dict(items: List[Tuple[bytes, str]]) -> Dict[str, Any]:
    """Read 1–5 same-day photos and merge figures from the best source."""
    from app.services.ai_vision_ocr import (
        ai_ocr_configured,
        extract_and_merge_register_images,
        missing_key_message,
    )

    if not items:
        return {"status": "ERROR", "error_detail": "No images uploaded"}
    if len(items) > 5:
        return {"status": "ERROR", "error_detail": "Upload at most 5 photos for the same day."}
    if not ai_ocr_configured():
        return {
            "status": "ERROR",
            "error_detail": missing_key_message(),
            "filename": items[0][1] if items else "",
            "file_size": len(items[0][0]) if items else 0,
            "last_step": "AI OCR not configured",
        }
    if len(items) == 1:
        return parse_image_to_dict(items[0][0], items[0][1])
    try:
        return extract_and_merge_register_images(items)
    except Exception as exc:
        logger.exception("Multi-image AI vision OCR failed")
        return {
            "status": "ERROR",
            "error_detail": str(exc),
            "filename": ", ".join(name for _, name in items),
            "last_step": "ONLINE AI VISION OCR",
        }


def parse_image_to_dict(image_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Full pipeline: raw image bytes -> accounting fields dict.
    Called by /api/imports/preview-image endpoint.
    """
    t0 = datetime.now()
    logger.info("[OCR] START  file=%s  size=%d",
                filename, len(image_bytes) if image_bytes else 0)

    # --- Validate ---
    val = validate_image(image_bytes)
    if not val["valid"]:
        logger.warning("[OCR] Validation failed: %s", val.get("error"))
        date_str = datetime.now().strftime("%Y-%m-%d")
        m = _DATE_PATTERN.search(filename or "")
        if m:
            date_str = _parse_date(*m.groups())
        empty_fields, _ = map_rows_to_fields([])
        preview = ""
        try:
            img, _, _ = _decode_to_bgr(image_bytes)
            if img is not None:
                preview = _data_url_jpeg(_encode_jpg(img, 80))
        except Exception:
            preview = ""
        return _sanitize({
            "status": "VALIDATION_WARNING",
            "error_detail": val.get("error", "Invalid image"),
            "date": date_str, "date_confidence": 0.5,
            "cash": None, "card_qr": None, "zomato": None,
            "swiggy": None, "dineout": None,
            "opening_balance": None, "site_expenses": None, "salary_advance": None,
            "fields": empty_fields, "parsed_rows": [], "itemized_expenses": [],
            "raw_ocr_response": [], "extraction_result": {}, "extraction_trace": {},
            "handwritten_total": None, "calculated_total": 0.0, "total_difference": 0.0,
            "image_b64": preview, "preprocessed_image_b64": preview, "amount_crop_b64": preview,
            "annotated_row_boxes_b64": preview, "raw_text": "", "processing_time_sec": 0.0,
        })

    logger.info("[OCR] Image OK  %dx%d  fmt=%s", int(val["w"]), int(val["h"]), val["format"])

    from app.services.ai_vision_ocr import (
        ai_ocr_configured,
        extract_daybook_with_ai,
        missing_key_message,
    )
    if not ai_ocr_configured():
        return {
            "status": "ERROR",
            "error_detail": missing_key_message(),
            "filename": filename,
            "file_size": len(image_bytes) if image_bytes else 0,
            "last_step": "AI OCR not configured",
        }
    try:
        return extract_daybook_with_ai(image_bytes, filename)
    except Exception as exc:
        logger.exception("Online AI vision OCR failed")
        return {
            "status": "ERROR",
            "error_detail": str(exc),
            "filename": filename,
            "file_size": len(image_bytes) if image_bytes else 0,
            "last_step": "ONLINE AI VISION OCR",
        }

    # --- Optimise + ledger preprocess ---
    opt_bytes, opt_img, _, _ = optimize_image(image_bytes, max_dim=1600)
    if opt_img is None:
        nparr = np.frombuffer(opt_bytes, np.uint8)
        opt_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if opt_img is None:
        opt_img = val["cv_img"]

    work_img, ocr_img = preprocess_ledger_image(opt_img)
    opt_img = work_img
    opt_bytes = _encode_jpg(opt_img, 85)
    b64_orig = b64_prep = b64_crop_col = ""

    # --- Full-page OCR on grid-suppressed page ---
    logger.info("[OCR] Full-page scan start")
    ocr_t0 = datetime.now()
    tokens = run_full_page_ocr(opt_bytes, img=ocr_img)
    logger.info("[OCR] Full-page scan done  %d tokens  %.1fs",
                len(tokens), (datetime.now() - ocr_t0).total_seconds())

    # --- Column boundaries ---
    bounds      = detect_column_bounds(opt_img, tokens)
    p_start     = bounds["p_start"]
    p_end       = bounds["p_end"]
    amt_rs_st   = bounds["amt_rs_start"]
    amt_rs_end  = bounds["amt_rs_end"]
    amt_ps_end  = bounds["amt_paise_end"]
    amt_ps_st   = bounds.get("amt_paise_start", amt_rs_end)
    logger.info("[OCR] Cols  particulars=%d-%d  amount=%d-%d",
                p_start, p_end, amt_rs_st, amt_rs_end)

    # --- Row grouping (keep the date row; do not drop the top 10%) ---
    h_img, w_img = opt_img.shape[:2]
    row_groups = group_tokens_into_rows(tokens, float(h_img), float(w_img))

    if not row_groups and tokens:
        band = max(30, int(h_img * 0.06))
        row_groups = []
        for i in range(min(15, int(h_img / band))):
            y1 = int(h_img * 0.10) + i * band
            row_groups.append([{
                "y_top": float(y1), "y_bottom": float(y1 + band),
                "y_center": float(y1 + band // 2),
                "x_left": 0.0, "x_right": float(w_img),
                "text": "", "confidence": 0.0,
            }])

    # --- Reconstruct rows ---
    reconstructed_rows: List[Dict[str, Any]] = []
    for idx, group in enumerate(row_groups, start=1):
        min_y = max(0, int(min(t["y_top"]    for t in group) - 6))
        max_y = min(h_img, int(max(t["y_bottom"] for t in group) + 6))

        # Date-column hash + particulars text. Folio "E" is appended as an expense marker.
        desc_tokens = [
            t["text"].strip()
            for t in sorted(group, key=lambda t: t["x_left"])
            if t["x_left"] < p_end and t["text"].strip()
        ]
        folio_tokens = [
            t["text"].strip()
            for t in group
            if p_end <= t["x_left"] < amt_rs_st and t["text"].strip()
        ]
        desc_raw = " ".join(desc_tokens).strip()
        folio_join = " ".join(folio_tokens).lower()
        if re.search(r"\be\b", folio_join) or re.search(r"\(\s*e\s*\)", folio_join):
            if "(e)" not in desc_raw.lower():
                desc_raw = (desc_raw + " (E)").strip()

        crop_rs   = opt_img[min_y:max_y, amt_rs_st:amt_rs_end]
        crop_full = opt_img[min_y:max_y, amt_rs_st:amt_ps_end]

        page_hint = amount_from_row_tokens(group, amt_rs_st, amt_ps_st)
        amt = extract_amount_from_crop(crop_rs, crop_full, page_hint=page_hint)

        desc_confs = [t["confidence"] for t in group if t["x_left"] < p_end]
        avg_dc = (float(np.mean(desc_confs)) if desc_confs
                  else float(np.mean([t["confidence"] for t in group])) if group
                  else 0.85)

        reconstructed_rows.append({
            "row_id":                   idx,
            "y_top":                    min_y,
            "y_bottom":                 max_y,
            "y_center":                 round((min_y + max_y) / 2.0, 1),
            "description_raw":          desc_raw,
            "description_normalized":   re.sub(r"[^a-z0-9\s]", "", desc_raw.lower()).strip(),
            "amount_raw":               amt["amount_raw"],
            "amount":                   amt["amount"],
            "amount_status":            amt["amount_status"],
            "description_confidence":   round(avg_dc, 2),
            "amount_confidence":        amt["ocr_confidence"],
            "numeric_validation_score": amt["numeric_validation_score"],
            "multi_pass_agreement":     amt["multi_pass_agreement"],
            "why_selected":             amt["why_selected"],
            "candidates":               amt["candidates"],
            "row_crop_b64":             "",
            "amount_crop_b64":          amt["amount_crop_b64"],
            "description_crop_b64":     "",
            "row_bbox":                 [0, min_y, w_img, max_y],
            "classification_confidence":0.0,
            "status":                   "UNCLASSIFIED",
        })

    logger.info("[OCR] %d rows reconstructed", len(reconstructed_rows))

    # Re-read amount cells that still look like folio/paise fragments vs Today Sale.
    today_guess = None
    for row in reconstructed_rows:
        cat_now, _ = classify_description(row["description_raw"])
        if cat_now == "TODAY_SALE" and row.get("amount"):
            today_guess = row["amount"]
            break
    weak_sales = max(80.0, (today_guess or 0) * 0.04)
    sales_like = {
        "CASH_SALE", "CARD_QR_PAYTM", "ZOMATO", "SWIGGY", "DINEOUT",
        "OPENING_CASH", "UNKNOWN",
    }
    recrop_n = 0
    for row in reconstructed_rows:
        cat_now, _ = classify_description(row["description_raw"])
        if cat_now in ("TODAY_SALE", "SERVICE_CHARGE", "SKIP_TOTAL"):
            continue
        if _is_date_only_row(row.get("description_raw", "")):
            continue
        amt = row.get("amount")
        needs = False
        if cat_now in sales_like:
            if amt is None:
                needs = True
            elif amt == 0 and cat_now != "CARD_QR_PAYTM":
                needs = True
            elif amt is not None and 0 < amt < weak_sales:
                needs = True
        elif cat_now in ("SITE_EXPENSE", "SALARY_ADVANCE") and (amt is None or (amt != 0 and amt < 10)):
            needs = True
        if not needs:
            continue
        y1, y2 = int(row["y_top"]), int(row["y_bottom"])
        crop_rs = opt_img[y1:y2, amt_rs_st:amt_rs_end]
        crop_full = opt_img[y1:y2, amt_rs_st:amt_ps_end]
        cropped = extract_amount_from_crop(crop_rs, crop_full, page_hint=None)
        new_amt = cropped.get("amount")
        if new_amt is None:
            continue
        if amt is None or _rupee_score(new_amt) > _rupee_score(amt) or (
            _rupee_score(new_amt) == _rupee_score(amt) and new_amt > amt
        ):
            row["amount"] = new_amt
            row["amount_raw"] = cropped.get("amount_raw", "")
            row["amount_status"] = cropped.get("amount_status", "REVIEW_REQUIRED")
            row["amount_confidence"] = cropped.get("ocr_confidence", 0)
            row["numeric_validation_score"] = cropped.get("numeric_validation_score", 0)
            row["why_selected"] = cropped.get("why_selected", "")
            row["candidates"] = cropped.get("candidates", [])
            recrop_n += 1
    if recrop_n:
        logger.info("[OCR] Re-read %d weak amount cells", recrop_n)

    # --- Field mapping ---
    field_mapping, itemized_expenses = map_rows_to_fields(reconstructed_rows)
    logger.info("[OCR] Field classification complete")

    # --- Date detection: image tokens first (WhatsApp filenames are the photo date, not the ledger date) ---
    detected_date = datetime.now().strftime("%Y-%m-%d")
    date_found = False
    date_blobs = [tok.get("text") or "" for tok in tokens[:12]]
    date_blobs.extend(r["description_raw"] for r in reconstructed_rows[:4])
    for blob in date_blobs:
        m = _DATE_PATTERN.search(blob)
        if m:
            detected_date = _parse_date(*m.groups())
            date_found = True
            break
    if not date_found:
        joined = " ".join(date_blobs)
        m = _DATE_PATTERN.search(joined)
        if m:
            detected_date = _parse_date(*m.groups())
            date_found = True
    if not date_found:
        fname = filename or ""
        camera_name = bool(re.search(r"whatsapp|img[-_]|screenshot|dcim", fname, re.I))
        m = _DATE_PATTERN.search(fname)
        if m and not camera_name:
            detected_date = _parse_date(*m.groups())

    # --- Totals ---
    cash    = field_mapping["cash"]["value"]    or 0.0
    card    = field_mapping["card_qr"]["value"] or 0.0
    zomato  = field_mapping["zomato"]["value"]  or 0.0
    swiggy  = field_mapping["swiggy"]["value"]  or 0.0
    dineout = field_mapping["dineout"]["value"] or 0.0
    calc_total = round(cash + card + zomato + swiggy + dineout, 2)

    handwritten_total = None
    for row in reconstructed_rows:
        d = row["description_normalized"]
        cat_now, _ = classify_description(row["description_raw"])
        if (cat_now == "TODAY_SALE" or any(kw in d for kw in ("today sale", "total sale", "gross sale", "todaysale"))) and row["amount"]:
            handwritten_total = row["amount"]
            break
    total_diff = round(handwritten_total - calc_total, 2) if handwritten_total is not None else 0.0

    # --- Annotated image ---
    annotated_b64 = ""

    # --- Diagnostic ---
    _print_diagnostic(reconstructed_rows, field_mapping, itemized_expenses)

    elapsed = round((datetime.now() - t0).total_seconds(), 2)
    logger.info("[OCR] DONE %.2fs  cash=%.0f card=%.0f zomato=%.0f swiggy=%.0f dineout=%.0f",
                elapsed, cash, card, zomato, swiggy, dineout)

    raw_ocr = [{"text": t["text"], "confidence": t["confidence"], "bbox": t.get("bbox", [])}
               for t in tokens]

    extraction_result = {
        "rows": reconstructed_rows,
        "sales": {
            "cash_sale":     field_mapping["cash"],
            "card_qr_paytm": field_mapping["card_qr"],
            "zomato":        field_mapping["zomato"],
            "swiggy":        field_mapping["swiggy"],
            "dineout":       field_mapping["dineout"],
        },
        "opening_cash":   field_mapping["opening_balance"],
        "expenses":       itemized_expenses,
        "salary_advance": field_mapping["salary_advance"],
    }

    return _sanitize({
        "status":                  "SUCCESS",
        "date":                    detected_date,
        "date_confidence":         0.85,
        "cash":                    field_mapping["cash"]["value"],
        "card_qr":                 field_mapping["card_qr"]["value"],
        "zomato":                  field_mapping["zomato"]["value"],
        "swiggy":                  field_mapping["swiggy"]["value"],
        "dineout":                 field_mapping["dineout"]["value"],
        "opening_balance":         field_mapping["opening_balance"]["value"],
        "site_expenses":           field_mapping["site_expenses"]["value"],
        "salary_advance":          field_mapping["salary_advance"]["value"],
        "fields":                  field_mapping,
        "parsed_rows":             reconstructed_rows,
        "itemized_expenses":       itemized_expenses,
        "extraction_result":       extraction_result,
        "extraction_trace":        extraction_result,
        "raw_ocr_response":        raw_ocr,
        "handwritten_total":       handwritten_total,
        "calculated_total":        calc_total,
        "total_difference":        total_diff,
        "image_b64":               f"data:image/jpeg;base64,{b64_orig}",
        "preprocessed_image_b64":  f"data:image/jpeg;base64,{b64_prep}",
        "amount_crop_b64":         f"data:image/jpeg;base64,{b64_crop_col}",
        "annotated_row_boxes_b64": (f"data:image/jpeg;base64,{annotated_b64}"
                                    if annotated_b64
                                    else f"data:image/jpeg;base64,{b64_orig}"),
        "raw_text":                "\n".join(
            r["description_raw"] + " " + (r["amount_raw"] or "")
            for r in reconstructed_rows
        ),
        "processing_time_sec":     elapsed,
    })


# ===========================================================================
# DataFrame wrapper
# ===========================================================================

def parse_image_to_dataframe(image_bytes: bytes, filename: str) -> pd.DataFrame:
    d = parse_image_to_dict(image_bytes, filename)
    return pd.DataFrame([{
        "Date":        d["date"],
        "Cash Sale":   d["cash"]    or 0.0,
        "Credit Card": d["card_qr"] or 0.0,
        "Zomato":      d["zomato"]  or 0.0,
        "Swiggy":      d["swiggy"]  or 0.0,
        "Dineout":     d["dineout"] or 0.0,
    }])


# ===========================================================================
# Reprocess-row helper  (used by /api/imports/reprocess-row endpoint)
# ===========================================================================

def analyze_isolated_row_crop(
    full_img: np.ndarray, row_id: int, y_top: int, y_bottom: int
) -> Dict[str, Any]:
    """Re-OCR a single row region. Used by the Reprocess button in the UI."""
    work, ocr_img = preprocess_ledger_image(full_img)
    h, w = work.shape[:2]
    y1, y2 = max(0, y_top), min(h, y_bottom)

    dummy_tokens = run_full_page_ocr(b"", img=ocr_img[y1:y2, :]) if y2 > y1 else []
    for t in dummy_tokens:
        t["y_top"] += y1
        t["y_bottom"] += y1
        t["y_center"] += y1
        if t.get("bbox") and len(t["bbox"]) >= 4:
            t["bbox"][1] += y1
            t["bbox"][3] += y1

    bounds = detect_column_bounds(work, dummy_tokens)
    amt_rs_st  = bounds["amt_rs_start"]
    amt_rs_end = bounds["amt_rs_end"]
    amt_ps_end = bounds["amt_paise_end"]
    amt_ps_st  = bounds.get("amt_paise_start", amt_rs_end)
    p_end      = bounds["p_end"]

    crop_rs   = work[y1:y2, amt_rs_st:amt_rs_end]
    crop_full = work[y1:y2, amt_rs_st:amt_ps_end]
    page_hint = amount_from_row_tokens(dummy_tokens, amt_rs_st, amt_ps_st)
    amt = extract_amount_from_crop(crop_rs, crop_full, page_hint=page_hint)

    row_b64 = ""
    try:
        _, buf = cv2.imencode(".jpg", work[y1:y2, :])
        row_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.tobytes()).decode()}"
    except Exception:
        pass

    desc_raw = f"Row {row_id}"
    desc_bits = [t["text"] for t in sorted(dummy_tokens, key=lambda t: t["x_left"]) if t["x_left"] < p_end]
    if desc_bits:
        desc_raw = " ".join(desc_bits).strip() or desc_raw
    elif _get_reader() is not None:
        try:
            tok = _easyocr_read(_get_reader(), ocr_img[y1:y2, 0:p_end])
            if tok:
                desc_raw = " ".join(t["text"] for t in tok if t["text"].strip()).strip() or desc_raw
        except Exception:
            pass

    cat, cat_conf = classify_description(desc_raw)
    return {
        "row_id":                   row_id,
        "y_top":                    y1, "y_bottom": y2,
        "y_center":                 round((y1 + y2) / 2.0, 1),
        "description_raw":          desc_raw,
        "description_normalized":   re.sub(r"[^a-z0-9\s]", "", desc_raw.lower()).strip(),
        "amount_raw":               amt["amount_raw"],
        "amount":                   amt["amount"],
        "amount_status":            amt["amount_status"],
        "description_confidence":   0.75,
        "amount_confidence":        amt["ocr_confidence"],
        "numeric_validation_score": amt["numeric_validation_score"],
        "candidates":               amt["candidates"],
        "why_selected":             amt["why_selected"],
        "amount_crop_b64":          amt["amount_crop_b64"],
        "row_crop_b64":             row_b64,
        "row_bbox":                 [0, y1, w, y2],
        "category":                 cat,
        "classification_confidence":cat_conf,
        "status":                   "UNCLASSIFIED",
    }


