#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 "BM-LBIT ver 2026 1.1" prepared by CA Bhadresh Mehta for benefit of various Libraries
================================================================================

PURPOSE
-------
A desktop (Tkinter) commercial-style standalone GUI application that:
  1. Lets the user pick a folder containing photographs of library book
     stacks / cupboards (books usually stored vertically, spines facing out).
  2. Reads every image in that folder, one at a time.
  3. Analyses each photo to detect INDIVIDUAL BOOKS (spine segmentation),
     then for every detected book tries to read:
        - Book Name / Title   (OCR - English & other languages via Tesseract
                                or Windows Native Media OCR)
        - Book Number / Code  (any barcode / QR code found on/near the
                                book via OpenCV barcode/QR detector or pyzbar,
                                or numeric token recognised by OCR)
        - Other Details       (any other readable text near the book - e.g.
                                author, edition, shelf mark, publisher line)
  4. Stores ONE ROW PER BOOK in a local SQLite database, including a small
     low-resolution JPEG thumbnail crop of that specific book (stored as a
     BLOB), so every book detected in every photo gets its own line item.
  5. Repeats until every image in the folder has been processed.
  6. Generates a formatted, print-ready Microsoft Excel (.xlsx) report with
     an embedded thumbnail image for every book row, ready to view or print.

OFFLINE / ON-PREMISE ARCHITECTURE
---------------------------------
This tool is designed to run fully OFFLINE / on-premise without requiring Python
or external cloud vision subscriptions:
   - OpenCV for spine/book boundary detection (colour-space and edge gradient analysis)
   - Dual OCR Engine:
       * Windows Native OCR (built into Windows 10 & 11, 100% offline, fast, zero setup)
       * Tesseract OCR (via pytesseract) auto-detected from standard Windows paths
   - Built-in OpenCV Barcode and QR-code detector + pyzbar fallback
   - OpenPyXL for formatted Excel report generation with embedded book thumbnail crops

Author / Prepared by : CA Bhadresh Mehta
Application Title    : "BM-LBIT ver 2026 1.1" prepared by CA Bhadresh Mehta for benefit of various Libraries
Short Name           : BM-LBIT
Version              : 2026-1.1
================================================================================
"""

import os
import io
import re
import sys
import glob
import random
import shutil
import sqlite3
import threading
import queue
import traceback
from datetime import datetime

# ---------------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError as e:
    sys.stderr.write(
        "ERROR: Tkinter is not installed for this Python interpreter.\n"
        "Debian/Ubuntu : sudo apt-get install -y python3-tk\n"
        "Windows/macOS : Tkinter ships with the official python.org installer.\n"
    )
    raise

try:
    import cv2
    import numpy as np
except ImportError:
    sys.stderr.write(
        "ERROR: opencv-python and numpy are required.\n"
        "    python -m pip install opencv-python numpy\n"
    )
    raise

try:
    from PIL import Image, ImageTk, ImageOps
except ImportError:
    sys.stderr.write(
        "ERROR: Pillow is required.\n"
        "    python -m pip install pillow\n"
    )
    raise

# Pytesseract detection & setup
try:
    import pytesseract
    PYTESSERACT_LIB_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_LIB_AVAILABLE = False

# Windows Native OCR (offline, built into Windows 10 & 11)
try:
    import winocr
    import asyncio
    WINOCR_AVAILABLE = True
except Exception:
    winocr = None
    WINOCR_AVAILABLE = False

# Barcode detectors
try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

CV2_BARCODE_AVAILABLE = hasattr(cv2, "barcode") and hasattr(cv2.barcode, "BarcodeDetector")
CV2_QR_AVAILABLE = hasattr(cv2, "QRCodeDetector")

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.worksheet.page import PageMargins
except ImportError:
    sys.stderr.write(
        "ERROR: openpyxl is required.\n"
        "    python -m pip install openpyxl\n"
    )
    raise


# ===========================================================================
#  CONFIGURATION & ENGINE AUTO-DETECTION
# ===========================================================================

APP_TITLE = '"BM-LBIT ver 2026 1.1" prepared by CA Bhadresh Mehta for benefit of various Libraries'
APP_SHORT_NAME = "BM-LBIT"

def _detect_tesseract_binary():
    """Auto-detects tesseract binary on PATH or standard install paths."""
    which = shutil.which("tesseract")
    if which and os.path.exists(which):
        return which
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Tesseract-OCR\tesseract.exe"),
        r"C:\tools\tesseract\tesseract.exe",
        r"C:\tesseract\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

TESSERACT_CMD = _detect_tesseract_binary()
TESSERACT_ACTIVE = False
if PYTESSERACT_LIB_AVAILABLE and TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_ACTIVE = True
    except Exception:
        TESSERACT_ACTIVE = False

OCR_LANGUAGES = "eng"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")
THUMBNAIL_MAX_SIZE = (160, 220)
THUMBNAIL_JPEG_QUALITY = 65
MIN_SPINE_WIDTH_PX = 24
DEFAULT_DB_FILENAME = "LBIT_Library_Books.db"


def get_engine_status_summary():
    """Returns a readable summary of active OCR and barcode backends."""
    ocr_parts = []
    if TESSERACT_ACTIVE:
        ocr_parts.append(f"Tesseract ({os.path.basename(TESSERACT_CMD)})")
    if WINOCR_AVAILABLE:
        ocr_parts.append("Windows Media OCR (Native Offline)")
    ocr_status = " + ".join(ocr_parts) if ocr_parts else "None available"

    bc_parts = []
    if CV2_BARCODE_AVAILABLE or CV2_QR_AVAILABLE:
        bc_parts.append("OpenCV Barcode/QR")
    if PYZBAR_AVAILABLE:
        bc_parts.append("pyzbar")
    bc_parts.append("OCR Numeric RegEx")
    bc_status = " + ".join(bc_parts)

    return f"Engine Ready | OCR: {ocr_status} | Code Reader: {bc_status}"


# ===========================================================================
#  RANDOM COLOUR THEME
# ===========================================================================

def _random_theme():
    palettes = [
        {"bg": "#0F2027", "panel": "#203A43", "accent": "#2C5364", "btn": "#3AA6B9", "text": "#EAF6F6", "hdr": "#0B7A75"},
        {"bg": "#1A1A2E", "panel": "#16213E", "accent": "#0F3460", "btn": "#E94560", "text": "#F1F1F1", "hdr": "#E94560"},
        {"bg": "#232526", "panel": "#2C2C34", "accent": "#3A3A3C", "btn": "#F2994A", "text": "#F5F5F5", "hdr": "#F2994A"},
        {"bg": "#134E5E", "panel": "#1B6B78", "accent": "#2F8F9D", "btn": "#71B280", "text": "#FFFFFF", "hdr": "#71B280"},
        {"bg": "#3E1E68", "panel": "#5B2C6F", "accent": "#7D3C98", "btn": "#F1948A", "text": "#FDF2FF", "hdr": "#F1948A"},
        {"bg": "#0B132B", "panel": "#1C2541", "accent": "#3A506B", "btn": "#5BC0BE", "text": "#EAF2F8", "hdr": "#5BC0BE"},
        {"bg": "#283618", "panel": "#3A5A40", "accent": "#588157", "btn": "#DDA15E", "text": "#FEFAE0", "hdr": "#DDA15E"},
        {"bg": "#3D0000", "panel": "#5A0A0A", "accent": "#7A1E1E", "btn": "#E8A87C", "text": "#FFF3E0", "hdr": "#E8A87C"},
        {"bg": "#1B262C", "panel": "#0F4C75", "accent": "#3282B8", "btn": "#BBE1FA", "text": "#F5F7FA", "hdr": "#3282B8"},
        {"bg": "#2B2118", "panel": "#41332A", "accent": "#6B4F3F", "btn": "#C9A66B", "text": "#F6EFE3", "hdr": "#C9A66B"},
    ]
    theme = random.choice(palettes)
    theme["btn_text"] = "#111111"
    return theme


# ===========================================================================
#  DATABASE LAYER
# ===========================================================================

class BookDatabase:
    """Thin SQLite wrapper - one row per detected book."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _conn(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL;")
        return self._local.conn

    def _init_schema(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                source_image   TEXT NOT NULL,
                book_index     INTEGER NOT NULL,
                book_name      TEXT,
                book_number    TEXT,
                other_details  TEXT,
                thumbnail      BLOB,
                thumb_width    INTEGER,
                thumb_height   INTEGER,
                created_at     TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                source_folder  TEXT NOT NULL,
                started_at     TEXT NOT NULL,
                finished_at    TEXT,
                images_scanned INTEGER DEFAULT 0,
                books_found    INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
        conn.close()

    def start_scan_log(self, folder):
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO scan_log (source_folder, started_at) VALUES (?, ?)",
            (folder, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return cur.lastrowid

    def finish_scan_log(self, log_id, images_scanned, books_found):
        conn = self._conn()
        conn.execute(
            "UPDATE scan_log SET finished_at=?, images_scanned=?, books_found=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), images_scanned, books_found, log_id),
        )
        conn.commit()

    def insert_book(self, source_image, book_index, book_name, book_number,
                     other_details, thumb_bytes, thumb_w, thumb_h):
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO books
                (source_image, book_index, book_name, book_number,
                 other_details, thumbnail, thumb_width, thumb_height, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_image, book_index, book_name, book_number, other_details,
                thumb_bytes, thumb_w, thumb_h,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()

    def fetch_all_books(self):
        conn = self._conn()
        cur = conn.execute(
            """
            SELECT id, source_image, book_index, book_name, book_number,
                   other_details, thumbnail, thumb_width, thumb_height, created_at
            FROM books
            ORDER BY source_image, book_index
            """
        )
        return cur.fetchall()

    def count_books(self):
        conn = self._conn()
        cur = conn.execute("SELECT COUNT(*) FROM books")
        return cur.fetchone()[0]

    def clear_all(self):
        conn = self._conn()
        conn.execute("DELETE FROM books")
        conn.execute("DELETE FROM scan_log")
        conn.commit()


# ===========================================================================
#  IMAGE PROCESSING & ANALYSIS ENGINE
# ===========================================================================

_BARCODE_LIKE_RE = re.compile(r"\b\d{4,13}\b")


def _read_image_safely(image_path):
    """Safely loads an image supporting full Unicode paths and EXIF auto-rotation."""
    try:
        pil_img = Image.open(image_path)
        pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return bgr
    except Exception:
        pass

    try:
        with open(image_path, "rb") as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            return bgr
    except Exception:
        return None


def _segment_book_spines(bgr_image):
    """
    Detects vertical book-spine boundaries in a shelf/stack photo and returns
    a list of (x_start, x_end) pixel column ranges.
    """
    h, w = bgr_image.shape[:2]
    if w < MIN_SPINE_WIDTH_PX:
        return [(0, w)]

    blur_k = max(9, (min(h, w) // 25) | 1)
    smooth = cv2.GaussianBlur(bgr_image, (blur_k, blur_k), 0)
    lab = cv2.cvtColor(smooth, cv2.COLOR_BGR2LAB).astype(np.float32)

    col_colour = lab.mean(axis=0)
    diffs = np.linalg.norm(np.diff(col_colour, axis=0), axis=1)
    if diffs.max() > 0:
        diffs_norm = diffs / diffs.max()
    else:
        diffs_norm = diffs

    k_size = min(5, max(1, len(diffs_norm)))
    diff_smooth = cv2.blur(diffs_norm.reshape(1, -1), (1, k_size)).flatten()

    std_val = float(np.std(diff_smooth))
    mean_val = float(np.mean(diff_smooth))
    threshold = max(mean_val + 1.4 * std_val, 0.18)
    min_spacing = max(MIN_SPINE_WIDTH_PX, w // 25)

    boundaries = [0]
    last_peak = -min_spacing
    n = len(diff_smooth)
    for x in range(1, n - 1):
        if (
            diff_smooth[x] > threshold
            and diff_smooth[x] >= diff_smooth[x - 1]
            and diff_smooth[x] >= diff_smooth[x + 1]
            and (x - last_peak) >= min_spacing
        ):
            boundaries.append(x + 1)
            last_peak = x
    boundaries.append(w)

    candidate_regions = []
    for i in range(len(boundaries) - 1):
        x0, x1 = boundaries[i], boundaries[i + 1]
        if (x1 - x0) >= MIN_SPINE_WIDTH_PX:
            candidate_regions.append((x0, x1))

    if not candidate_regions:
        return [(0, w)]

    region_widths = [x1 - x0 for x0, x1 in candidate_regions]
    avg_width = sum(region_widths) / len(region_widths)
    avg_width_ratio = avg_width / w

    too_many_regions = len(candidate_regions) > 50
    slivered = avg_width_ratio < 0.015 and len(candidate_regions) >= 4

    if too_many_regions or slivered:
        return [(0, w)]

    return candidate_regions


def _preprocess_for_ocr(crop_bgr, mode="thresh"):
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    scale = 2 if max(h, w) < 900 else 1
    if scale != 1:
        gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    if mode == "gray":
        return cv2.equalizeHist(gray)

    gray = cv2.bilateralFilter(gray, 7, 50, 50)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    return thresh


def _is_useful_token(tok):
    if not tok:
        return False
    alnum_count = sum(ch.isalnum() for ch in tok)
    if alnum_count == 0:
        return False
    if alnum_count / len(tok) < 0.80:
        return False
    if len(tok) <= 2 and tok.isalpha():
        return False
    return True


def _ocr_with_winocr(pil_crop):
    """Runs Windows Media OCR (offline, built into Windows 10/11) across multiple angles."""
    if not WINOCR_AVAILABLE:
        return ""

    async def _run():
        best_text = ""
        best_score = -1
        for rot in (0, 90, 270):
            try:
                img = pil_crop.rotate(rot, expand=True) if rot != 0 else pil_crop
                res = await winocr.recognize_pil(img, 'en')
                words = []
                for line in res.lines:
                    for w in line.words:
                        txt = w.text.strip()
                        if _is_useful_token(txt):
                            words.append(txt)
                text = " ".join(words).strip()
                score = len(text)
                if score > best_score and text:
                    best_score = score
                    best_text = text
            except Exception:
                continue
        return best_text

    try:
        return asyncio.run(_run())
    except Exception:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, _run()).result()
            else:
                return loop.run_until_complete(_run())
        except Exception:
            return ""


def _ocr_with_tesseract(crop_bgr):
    """Runs Tesseract OCR across 4 orientations and 2 preprocessing passes."""
    if not TESSERACT_ACTIVE:
        return ""

    best_text = ""
    best_score = -1.0
    rotations = {
        0: crop_bgr,
        90: cv2.rotate(crop_bgr, cv2.ROTATE_90_CLOCKWISE),
        180: cv2.rotate(crop_bgr, cv2.ROTATE_180),
        270: cv2.rotate(crop_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE),
    }
    for angle, variant in rotations.items():
        for mode in ("thresh", "gray"):
            try:
                pre = _preprocess_for_ocr(variant, mode=mode)
                data = pytesseract.image_to_data(
                    pre, lang=OCR_LANGUAGES, output_type=pytesseract.Output.DICT,
                    config="--psm 6"
                )
                words = []
                confs = []
                for txt, conf in zip(data["text"], data["conf"]):
                    txt = txt.strip()
                    if not _is_useful_token(txt):
                        continue
                    try:
                        c = float(conf)
                    except (ValueError, TypeError):
                        c = -1
                    if c >= 40:
                        words.append(txt)
                        confs.append(c)
                text = " ".join(words).strip()
                avg_conf = (sum(confs) / len(confs)) if confs else 0
                total_chars = sum(len(w) for w in words)
                score = avg_conf * total_chars
                if score > best_score and text:
                    best_score = score
                    best_text = text
            except Exception:
                continue
    return best_text


def _ocr_best_orientation(crop_bgr):
    """Unified OCR dispatcher choosing Tesseract or Windows Media OCR."""
    text = ""
    if TESSERACT_ACTIVE:
        text = _ocr_with_tesseract(crop_bgr)
    if not text and WINOCR_AVAILABLE:
        try:
            rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            pil_crop = Image.fromarray(rgb)
            text = _ocr_with_winocr(pil_crop)
        except Exception:
            pass
    return text


def _clean_title_text(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", raw_text).strip()
    tokens = [t for t in text.split(" ") if _is_useful_token(t)]
    return " ".join(tokens)[:180]


def _find_barcode_or_number(crop_bgr, ocr_text):
    """
    Decodes barcode/QR or falls back to numeric tokens from OCR.
    Compatible with OpenCV 4.x, OpenCV 5.x, pyzbar, and regex.
    """
    if CV2_BARCODE_AVAILABLE:
        try:
            bd = cv2.barcode.BarcodeDetector()
            res = bd.detectAndDecode(crop_bgr)
            decoded_info = res[1] if len(res) == 4 else res[0]
            if decoded_info:
                if isinstance(decoded_info, (list, tuple)):
                    vals = [str(x).strip() for x in decoded_info if x and str(x).strip()]
                    if vals:
                        return ("; ".join(vals), "barcode")
                elif str(decoded_info).strip():
                    return (str(decoded_info).strip(), "barcode")
        except Exception:
            pass

    if CV2_QR_AVAILABLE:
        try:
            qrd = cv2.QRCodeDetector()
            res = qrd.detectAndDecodeMulti(crop_bgr)
            if len(res) >= 2:
                retval, decoded_info = res[0], res[1]
                if retval and decoded_info:
                    if isinstance(decoded_info, (list, tuple)):
                        vals = [str(x).strip() for x in decoded_info if x and str(x).strip()]
                        if vals:
                            return ("; ".join(vals), "barcode")
                    elif str(decoded_info).strip():
                        return (str(decoded_info).strip(), "barcode")
        except Exception:
            pass

    if PYZBAR_AVAILABLE:
        try:
            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            results = zbar_decode(gray)
            if results:
                values = [r.data.decode("utf-8", errors="ignore") for r in results]
                return ("; ".join(values), "barcode")
        except Exception:
            pass

    match = _BARCODE_LIKE_RE.search(ocr_text or "")
    if match:
        return (match.group(0), "ocr-numeric")

    return ("", "none")


def _make_thumbnail_bytes(crop_bgr):
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    pil_img.thumbnail(THUMBNAIL_MAX_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=THUMBNAIL_JPEG_QUALITY)
    return buf.getvalue(), pil_img.width, pil_img.height


def analyze_image(image_path, log_fn=None):
    """Main image analysis pipeline for one photo."""
    def log(msg):
        if log_fn:
            log_fn(msg)

    bgr = _read_image_safely(image_path)
    if bgr is None:
        log(f"    Could not read image: {os.path.basename(image_path)}; skipping.")
        return []

    h, w = bgr.shape[:2]
    max_dim = 2200
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        bgr_small = cv2.resize(bgr, (int(w * scale), int(h * scale)))
    else:
        bgr_small = bgr
        scale = 1.0

    regions_small = _segment_book_spines(bgr_small)
    log(f"    Detected {len(regions_small)} candidate book region(s).")

    results = []
    for idx, (x0s, x1s) in enumerate(regions_small, start=1):
        x0 = int(x0s / scale)
        x1 = int(x1s / scale)
        x0 = max(0, min(x0, w - 1))
        x1 = max(x0 + 1, min(x1, w))
        crop = bgr[:, x0:x1]

        if crop.size == 0 or crop.shape[0] == 0 or crop.shape[1] == 0:
            continue

        ocr_text = _ocr_best_orientation(crop)
        book_name = _clean_title_text(ocr_text)
        book_number, method = _find_barcode_or_number(crop, ocr_text)

        other_bits = []
        if method == "barcode":
            other_bits.append("Code: scanned barcode/QR")
        elif method == "ocr-numeric":
            other_bits.append("Code: OCR numeric token")
        other_bits.append(f"Spine px: {x0}-{x1} of {w}")
        if not book_name:
            other_bits.append("Title not detected")
        other_details = " | ".join(other_bits)

        thumb_bytes, tw, th = _make_thumbnail_bytes(crop)

        results.append(
            {
                "book_name": book_name if book_name else "(Title not detected)",
                "book_number": book_number,
                "other_details": other_details,
                "thumb_bytes": thumb_bytes,
                "thumb_w": tw,
                "thumb_h": th,
            }
        )

    return results


# ===========================================================================
#  EXCEL REPORT GENERATION
# ===========================================================================

def export_books_to_excel(rows, xlsx_path, progress_cb=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Library Books"

    headers = [
        "Sr. No.", "Source Photo", "Book # in Photo", "Book Name",
        "Book Number / Code", "Other Details", "Thumbnail", "Date Catalogued",
    ]

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    thin = Side(style="thin", color="AAAAAA")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap_center = Alignment(wrap_text=True, vertical="center", horizontal="left")

    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = border

    col_widths = [8, 26, 12, 34, 20, 44, 20, 18]
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    THUMB_ROW_HEIGHT = 92
    total = len(rows)

    for i, row in enumerate(rows, start=1):
        (rid, source_image, book_index, book_name, book_number,
         other_details, thumb_blob, tw, th, created_at) = row

        r = i + 1
        ws.cell(row=r, column=1, value=i).border = border
        ws.cell(row=r, column=2, value=os.path.basename(source_image)).border = border
        ws.cell(row=r, column=3, value=book_index).border = border
        c4 = ws.cell(row=r, column=4, value=book_name or "")
        c4.border = border
        c4.alignment = wrap_center
        c5 = ws.cell(row=r, column=5, value=book_number or "")
        c5.border = border
        c5.alignment = wrap_center
        c6 = ws.cell(row=r, column=6, value=other_details or "")
        c6.border = border
        c6.alignment = wrap_center
        ws.cell(row=r, column=8, value=created_at).border = border
        ws.cell(row=r, column=7, value="").border = border

        ws.row_dimensions[r].height = THUMB_ROW_HEIGHT

        if thumb_blob:
            try:
                img_stream = io.BytesIO(thumb_blob)
                xl_img = XLImage(img_stream)
                max_h_px = int(THUMB_ROW_HEIGHT * 1.33)
                if xl_img.height > max_h_px:
                    ratio = max_h_px / xl_img.height
                    xl_img.width = int(xl_img.width * ratio)
                    xl_img.height = max_h_px
                anchor_cell = f"G{r}"
                ws.add_image(xl_img, anchor_cell)
            except Exception:
                ws.cell(row=r, column=7, value="[image error]")

        if progress_cb and (i % 10 == 0 or i == total):
            progress_cb(i, total)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:H{max(1, len(rows) + 1)}"

    ws.print_title_rows = "1:1"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.4, right=0.4, top=0.6, bottom=0.5,
                                   header=0.3, footer=0.3)
    ws.oddHeader.center.text = APP_TITLE
    ws.oddHeader.center.size = 10
    ws.oddFooter.right.text = "Page &P of &N"
    ws.oddFooter.left.text = "Generated &D &T"
    ws.print_area = f"A1:H{max(1, len(rows) + 1)}"

    ws2 = wb.create_sheet("Summary")
    ws2["A1"] = APP_TITLE
    ws2["A1"].font = Font(bold=True, size=12)
    ws2["A3"] = "Total books catalogued:"
    ws2["B3"] = len(rows)
    ws2["A4"] = "Report generated:"
    ws2["B4"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws2["A5"] = "Distinct source photos:"
    ws2["B5"] = len({row[1] for row in rows}) if rows else 0
    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 28

    wb.save(xlsx_path)
    return xlsx_path


# ===========================================================================
#  GUI APPLICATION
# ===========================================================================

class LBITApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.theme = _random_theme()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(900, 560)
        self.configure(bg=self.theme["bg"])

        self._is_expanded = False
        self._folder_path = tk.StringVar(value="")
        self._db_path = tk.StringVar(value="")
        self._status_text = tk.StringVar(value="Ready. Please select a photo folder to begin.")
        self._progress_value = tk.DoubleVar(value=0.0)

        self._worker_thread = None
        self._msg_queue = queue.Queue()
        self._db = None
        self._cancel_requested = threading.Event()

        self._build_style()
        self._build_layout()
        self._poll_queue()

        # Log banner and active engines on startup
        self._log(APP_TITLE)
        self._log(get_engine_status_summary())

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        t = self.theme
        style.configure("TFrame", background=t["bg"])
        style.configure("Panel.TFrame", background=t["panel"])
        style.configure("TLabel", background=t["bg"], foreground=t["text"], font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=t["bg"], foreground=t["text"],
                         font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background=t["bg"], foreground=t["text"],
                         font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background=t["panel"], foreground=t["text"],
                         font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.map("TButton",
                  background=[("!disabled", t["btn"]), ("active", t["accent"])],
                  foreground=[("!disabled", t["btn_text"])])
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TEntry", fieldbackground="#FFFFFF", padding=4)
        style.configure("Horizontal.TProgressbar", troughcolor=t["panel"],
                         background=t["btn"], thickness=16)
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                         foreground="#222222", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=t["hdr"], foreground="#FFFFFF",
                         font=("Segoe UI", 9, "bold"))

    def _build_layout(self):
        t = self.theme

        # Banner with required title page caption
        banner = tk.Frame(self, bg=t["hdr"], height=62)
        banner.pack(side="top", fill="x")
        tk.Label(
            banner, text=APP_TITLE, bg=t["hdr"], fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"), anchor="w", padx=14, wraplength=950, justify="left"
        ).pack(side="left", fill="y", pady=6)

        self._expand_btn = tk.Button(
            banner, text="⤢  Expand Screen", command=self._toggle_expand,
            bg=t["btn"], fg=t["btn_text"], font=("Segoe UI", 10, "bold"),
            relief="flat", padx=10, cursor="hand2",
        )
        self._expand_btn.pack(side="right", padx=10, pady=10)

        # Top panel
        top_panel = tk.Frame(self, bg=t["panel"], padx=14, pady=12)
        top_panel.pack(side="top", fill="x")

        tk.Label(top_panel, text="Step 1 - Photo Folder:", bg=t["panel"], fg=t["text"],
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        folder_entry = tk.Entry(top_panel, textvariable=self._folder_path, width=70,
                                 font=("Segoe UI", 10))
        folder_entry.grid(row=0, column=1, padx=8, sticky="we")
        tk.Button(top_panel, text="Browse Folder...", command=self._choose_folder,
                  bg=t["btn"], fg=t["btn_text"], relief="flat", padx=10,
                  cursor="hand2").grid(row=0, column=2, padx=4)

        tk.Label(top_panel, text="Database File:", bg=t["panel"], fg=t["text"],
                  font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        db_entry = tk.Entry(top_panel, textvariable=self._db_path, width=70,
                             font=("Segoe UI", 10))
        db_entry.grid(row=1, column=1, padx=8, sticky="we", pady=(8, 0))
        tk.Button(top_panel, text="Choose DB Location...", command=self._choose_db_path,
                  bg=t["btn"], fg=t["btn_text"], relief="flat", padx=10,
                  cursor="hand2").grid(row=1, column=2, padx=4, pady=(8, 0))

        top_panel.grid_columnconfigure(1, weight=1)

        # Action bar
        action_bar = tk.Frame(self, bg=t["bg"], pady=10)
        action_bar.pack(side="top", fill="x", padx=14)

        self._scan_btn = tk.Button(
            action_bar, text="▶  Start Scanning Photos", command=self._start_scan,
            bg=t["btn"], fg=t["btn_text"], font=("Segoe UI", 11, "bold"),
            relief="flat", padx=16, pady=8, cursor="hand2",
        )
        self._scan_btn.pack(side="left", padx=(0, 8))

        self._cancel_btn = tk.Button(
            action_bar, text="■  Cancel", command=self._cancel_scan,
            bg="#B03A2E", fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=12, pady=8, cursor="hand2", state="disabled",
        )
        self._cancel_btn.pack(side="left", padx=8)

        self._export_btn = tk.Button(
            action_bar, text="⬇  Generate Excel Report (View / Print)",
            command=self._export_excel,
            bg=t["accent"], fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=12, pady=8, cursor="hand2",
        )
        self._export_btn.pack(side="left", padx=8)

        self._clear_btn = tk.Button(
            action_bar, text="🗑  Clear Database", command=self._clear_database,
            bg="#555555", fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=12, pady=8, cursor="hand2",
        )
        self._clear_btn.pack(side="left", padx=8)

        self._book_count_lbl = tk.Label(
            action_bar, text="Books catalogued: 0", bg=t["bg"], fg=t["text"],
            font=("Segoe UI", 10, "bold"),
        )
        self._book_count_lbl.pack(side="right", padx=10)

        # Progress bar
        prog_frame = tk.Frame(self, bg=t["bg"])
        prog_frame.pack(side="top", fill="x", padx=14, pady=(0, 6))
        self._progress_bar = ttk.Progressbar(
            prog_frame, orient="horizontal", mode="determinate",
            variable=self._progress_value, maximum=100,
        )
        self._progress_bar.pack(fill="x")

        status_lbl = tk.Label(self, textvariable=self._status_text, bg=t["bg"],
                               fg=t["text"], anchor="w", font=("Segoe UI", 9, "italic"))
        status_lbl.pack(side="top", fill="x", padx=16, pady=(0, 6))

        # Draggable Paned layout
        self._paned = tk.PanedWindow(self, orient="vertical", sashrelief="raised",
                                      sashwidth=6, bg=t["accent"])
        self._paned.pack(side="top", fill="both", expand=True, padx=14, pady=(0, 12))

        # Log frame
        log_frame = tk.Frame(self._paned, bg=t["panel"])
        tk.Label(log_frame, text="Activity Log", bg=t["panel"], fg=t["text"],
                  font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=8, pady=(6, 0))
        log_inner = tk.Frame(log_frame, bg=t["panel"])
        log_inner.pack(fill="both", expand=True, padx=8, pady=6)
        self._log_text = tk.Text(log_inner, height=8, wrap="word", bg="#0D0D0D",
                                  fg="#7CFC7C", insertbackground="#7CFC7C",
                                  font=("Consolas", 9))
        log_scroll = tk.Scrollbar(log_inner, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        self._paned.add(log_frame, minsize=100)

        # Table frame
        results_frame = tk.Frame(self._paned, bg=t["panel"])
        tk.Label(results_frame, text="Detected Books (this session)", bg=t["panel"],
                  fg=t["text"], font=("Segoe UI", 10, "bold"),
                  anchor="w").pack(fill="x", padx=8, pady=(6, 0))
        table_inner = tk.Frame(results_frame, bg=t["panel"])
        table_inner.pack(fill="both", expand=True, padx=8, pady=6)

        columns = ("photo", "idx", "name", "number", "details")
        self._tree = ttk.Treeview(table_inner, columns=columns, show="headings", height=10)
        self._tree.heading("photo", text="Source Photo")
        self._tree.heading("idx", text="#")
        self._tree.heading("name", text="Book Name")
        self._tree.heading("number", text="Book Number / Code")
        self._tree.heading("details", text="Other Details")
        self._tree.column("photo", width=160, anchor="w")
        self._tree.column("idx", width=40, anchor="center")
        self._tree.column("name", width=260, anchor="w")
        self._tree.column("number", width=150, anchor="w")
        self._tree.column("details", width=380, anchor="w")

        tree_scroll_y = ttk.Scrollbar(table_inner, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_scroll_y.set)
        self._tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")

        self._paned.add(results_frame, minsize=140)

    def _set_ui_scanning(self, is_scanning):
        if is_scanning:
            self._scan_btn.configure(state="disabled")
            self._cancel_btn.configure(state="normal")
            self._export_btn.configure(state="disabled")
            self._clear_btn.configure(state="disabled")
        else:
            self._scan_btn.configure(state="normal")
            self._cancel_btn.configure(state="disabled")
            self._export_btn.configure(state="normal")
            self._clear_btn.configure(state="normal")

    def _log(self, message):
        self._msg_queue.put(("log", message))

    def _append_log_line(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{ts}] {message}\n")
        self._log_text.see("end")

    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded
        if self._is_expanded:
            try:
                self.state("zoomed")
            except tk.TclError:
                self.attributes("-zoomed", True)
            self._expand_btn.configure(text="⤡  Contract Screen")
        else:
            try:
                self.state("normal")
            except tk.TclError:
                self.attributes("-zoomed", False)
            self.geometry("1180x760")
            self._expand_btn.configure(text="⤢  Expand Screen")

    def _choose_folder(self):
        path = filedialog.askdirectory(title="Select the folder containing library book photos")
        if path:
            self._folder_path.set(path)
            if not self._db_path.get():
                self._db_path.set(os.path.join(path, DEFAULT_DB_FILENAME))
            self._status_text.set(f"Folder selected: {path}")

    def _choose_db_path(self):
        initial_dir = self._folder_path.get() or os.getcwd()
        path = filedialog.asksaveasfilename(
            title="Choose / create the SQLite database file",
            initialdir=initial_dir,
            initialfile=DEFAULT_DB_FILENAME,
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if path:
            self._db_path.set(path)

    def _get_or_create_db(self):
        db_path = self._db_path.get().strip()
        if not db_path:
            folder = self._folder_path.get().strip()
            if not folder:
                messagebox.showwarning(APP_SHORT_NAME, "Please select a photo folder first.")
                return None
            db_path = os.path.join(folder, DEFAULT_DB_FILENAME)
            self._db_path.set(db_path)
        if self._db is None or self._db.db_path != db_path:
            self._db = BookDatabase(db_path)
        return self._db

    def _refresh_book_count(self):
        db = self._db
        if db:
            try:
                count = db.count_books()
                self._book_count_lbl.configure(text=f"Books catalogued: {count}")
            except Exception:
                pass

    def _start_scan(self):
        folder = self._folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(APP_SHORT_NAME, "Please select a valid photo folder first.")
            return

        db = self._get_or_create_db()
        if db is None:
            return

        image_files = sorted(
            f for f in glob.glob(os.path.join(folder, "*"))
            if f.lower().endswith(IMAGE_EXTENSIONS) and not os.path.basename(f).startswith(".")
        )
        if not image_files:
            messagebox.showinfo(
                APP_SHORT_NAME,
                f"No supported image files were found in:\n{folder}\n\n"
                f"Supported types: {', '.join(IMAGE_EXTENSIONS)}",
            )
            return

        self._tree.delete(*self._tree.get_children())
        self._log_text.delete("1.0", "end")
        self._progress_value.set(0)
        self._cancel_requested.clear()

        self._set_ui_scanning(True)

        self._worker_thread = threading.Thread(
            target=self._scan_worker, args=(folder, image_files, db), daemon=True
        )
        self._worker_thread.start()

    def _cancel_scan(self):
        self._cancel_requested.set()
        self._log("Cancellation requested - stopping gracefully...")

    def _scan_worker(self, folder, image_files, db):
        total = len(image_files)
        self._msg_queue.put(("status", f"Scanning {total} photo(s) in {folder} ..."))
        self._log(f"Found {total} photo(s) to analyse in: {folder}")

        log_id = db.start_scan_log(folder)
        total_books = 0

        for i, image_path in enumerate(image_files, start=1):
            if self._cancel_requested.is_set():
                self._log("Scan cancelled by user.")
                break

            fname = os.path.basename(image_path)
            self._log(f"[{i}/{total}] Analysing photo: {fname}")

            try:
                books = analyze_image(image_path, log_fn=self._log)
            except Exception as e:
                self._log(f"    ERROR analysing {fname}: {e}")
                self._log(traceback.format_exc(limit=2))
                books = []

            for b_idx, book in enumerate(books, start=1):
                db.insert_book(
                    source_image=image_path,
                    book_index=b_idx,
                    book_name=book["book_name"],
                    book_number=book["book_number"],
                    other_details=book["other_details"],
                    thumb_bytes=book["thumb_bytes"],
                    thumb_w=book["thumb_w"],
                    thumb_h=book["thumb_h"],
                )
                total_books += 1
                self._msg_queue.put((
                    "row",
                    (fname, b_idx, book["book_name"], book["book_number"], book["other_details"]),
                ))

            self._log(f"    -> {len(books)} book(s) catalogued from this photo.")
            self._msg_queue.put(("progress", i / total * 100.0))
            self._msg_queue.put(("count", None))

        db.finish_scan_log(log_id, images_scanned=total, books_found=total_books)
        self._msg_queue.put(("status", f"Done. {total_books} book(s) catalogued from {total} photo(s)."))
        self._msg_queue.put(("scan_complete", None))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "log":
                    self._append_log_line(payload)
                elif kind == "status":
                    self._status_text.set(payload)
                elif kind == "progress":
                    self._progress_value.set(payload)
                elif kind == "row":
                    fname, b_idx, name, number, details = payload
                    self._tree.insert("", "end", values=(fname, b_idx, name, number, details))
                elif kind == "count":
                    self._refresh_book_count()
                elif kind == "scan_complete":
                    self._set_ui_scanning(False)
                    self._refresh_book_count()
        except queue.Empty:
            pass
        except Exception as e:
            sys.stderr.write(f"Queue error: {e}\n")
        finally:
            self.after(120, self._poll_queue)

    def _export_excel(self):
        db = self._get_or_create_db()
        if db is None:
            return
        rows = db.fetch_all_books()
        if not rows:
            messagebox.showinfo(APP_SHORT_NAME, "No books have been catalogued yet. Run a scan first.")
            return

        default_name = f"BM_LBIT_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        initial_dir = os.path.dirname(self._db_path.get()) if self._db_path.get() else os.getcwd()
        xlsx_path = filedialog.asksaveasfilename(
            title="Save Excel Report As",
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not xlsx_path:
            return

        self._status_text.set("Generating Excel report...")
        self.update_idletasks()

        def do_export():
            try:
                export_books_to_excel(rows, xlsx_path)
                self._msg_queue.put(("log", f"Excel report saved: {xlsx_path}"))
                self._msg_queue.put(("status", f"Excel report saved: {xlsx_path}"))
                self.after(0, lambda: messagebox.showinfo(
                    APP_SHORT_NAME,
                    f"Excel report generated successfully:\n{xlsx_path}\n\n"
                    "Open it in Excel to VIEW the catalogue, or use "
                    "File > Print (landscape, fit-to-page is pre-set)."
                ))
            except PermissionError:
                self.after(0, lambda: messagebox.showerror(
                    APP_SHORT_NAME,
                    f"Permission Denied: Could not save to:\n{xlsx_path}\n\n"
                    "The file appears to be open in Microsoft Excel or another program.\n"
                    "Please close the file and try again."
                ))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror(
                    APP_SHORT_NAME, f"Failed to generate Excel report:\n{err}"
                ))

        threading.Thread(target=do_export, daemon=True).start()

    def _clear_database(self):
        db = self._get_or_create_db()
        if db is None:
            return
        if not messagebox.askyesno(
            APP_SHORT_NAME,
            "This will permanently delete ALL catalogued book records from "
            "the current database file. Continue?",
        ):
            return
        db.clear_all()
        self._tree.delete(*self._tree.get_children())
        self._refresh_book_count()
        self._log("Database cleared by user.")

    def _on_close(self):
        if self._worker_thread and self._worker_thread.is_alive():
            if not messagebox.askyesno(
                APP_SHORT_NAME, "A scan is still running. Exit anyway?"
            ):
                return
            self._cancel_requested.set()
        self.destroy()


def main():
    app = LBITApp()
    app.mainloop()


if __name__ == "__main__":
    main()
