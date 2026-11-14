"""
rename_stamped_copies.py  -  Offline renamer for stamped invoice copies
=========================================================================
Reads the invoice number printed on each scanned stamped copy (JPG / PNG / PDF)
and saves it as a PDF named by that number, ready for upload to the Zoho Books
Documents folder "STAMPED COPIES - SALE INVOICES".  Output is ALWAYS PDF.

  WhatsApp Image 2026-10-25 at 10.14.32.jpeg  ->  numbered/INV-OCT-000001.pdf
  Scanned_20261025-1532 (1).pdf               ->  numbered/INV-OCT-B-000003.pdf

100% offline: OCR runs on this computer. Nothing is uploaded anywhere.
Originals are never changed (files are COPIED into the "numbered" folder).

USAGE (Command Prompt, inside the scans folder):
    python rename_stamped_copies.py
    python rename_stamped_copies.py "A:\\AICA Level-2\\25-10-2026\\scanned copies"
Options:
    --no-prompt   do not ask for numbers that could not be read (just log them)
    --move        move instead of copy (originals removed from the scans folder)

ONE-TIME SETUP (needs internet only for the install):
    pip install rapidocr-onnxruntime pymupdf pillow
  If rapidocr will not install on your Python version, use Tesseract instead:
    pip install pytesseract pymupdf pillow
    + install Tesseract-OCR for Windows (UB Mannheim build) to the default path
"""

import csv
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime

from PIL import Image, ImageOps

# ----------------------------- SETTINGS ---------------------------------
OUTPUT_FOLDER = "numbered"           # numbered copies go here
UNMATCHED_FOLDER = "unmatched"       # files whose number could not be found
LOG_FILE = "rename_log.csv"
EXTENSIONS = (".jpg", ".jpeg", ".png", ".pdf")
# Invoice number formats: INV-000363, INV-OCT-000001, INV-OCT-B-000003, INV-4664205
INVOICE_REGEX = re.compile(r"INV-(?:[A-Z]{1,6}-){0,3}[0-9O]{3,}")
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
# -------------------------------------------------------------------------


# ============================ OCR ENGINES ================================
_engine = None


def get_engine():
    """RapidOCR if installed (pip-only, models bundled), else Tesseract."""
    global _engine
    if _engine:
        return _engine
    try:
        from rapidocr_onnxruntime import RapidOCR
        rapid = RapidOCR()

        def run_rapid(img):
            import numpy as np
            result, _ = rapid(np.array(img.convert("RGB")))
            return "\n".join(r[1] for r in (result or []))

        _engine = ("RapidOCR", run_rapid)
        return _engine
    except Exception:
        pass
    try:
        import pytesseract
        for p in TESSERACT_PATHS:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
        pytesseract.get_tesseract_version()

        def run_tess(img):
            g = ImageOps.grayscale(img)
            t1 = pytesseract.image_to_string(g)
            if INVOICE_REGEX.search(normalise(t1)):
                return t1
            return t1 + "\n" + pytesseract.image_to_string(g, config="--psm 11")

        _engine = ("Tesseract", run_tess)
        return _engine
    except Exception:
        sys.exit(
            "\nNo OCR engine found.\n"
            "Run:  pip install rapidocr-onnxruntime pymupdf pillow\n"
            "(or install pytesseract + Tesseract-OCR, see top of this file)\n"
        )


# ============================ TEXT HELPERS ===============================
def normalise(text):
    t = text.upper()
    t = t.replace("\u2013", "-").replace("\u2014", "-").replace("_", "-")
    t = re.sub(r"\s*-\s*", "-", t)            # "INV - OCT - 000001" -> "INV-OCT-000001"
    t = re.sub(r"\bINV\s+(?=[A-Z0-9])", "INV-", t)  # "INV 000363" -> "INV-000363"
    t = t.replace("1NV-", "INV-").replace("LNV-", "INV-")
    return t


def find_invoice_number(text):
    found = []
    for m in INVOICE_REGEX.findall(normalise(text)):
        parts = m.split("-")
        parts[-1] = parts[-1].replace("O", "0")  # OCR O/0 confusion in the number part
        found.append("-".join(parts))
    if not found:
        return None
    # most frequent reading wins (header and totals often repeat the number)
    return Counter(found).most_common(1)[0][0]


# ============================ FILE READERS ===============================
def pdf_text_and_image(path):
    """Embedded text (if any) + first page as image (for OCR)."""
    text, img = "", None
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        page = doc[0]
        text = page.get_text()
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return text, img
    except ImportError:
        pass
    # fallback without PyMuPDF: pypdf text + largest embedded image (scanned PDFs)
    from pypdf import PdfReader
    page = PdfReader(path).pages[0]
    text = page.extract_text() or ""
    imgs = sorted(page.images, key=lambda i: len(i.data), reverse=True)
    if imgs:
        img = imgs[0].image
    return text, img


def ocr_with_rotations(img):
    """Phone photos are sometimes sideways/upside down: try 0, 90, 270, 180."""
    name, run = get_engine()
    img = ImageOps.exif_transpose(img)
    if max(img.size) < 1800:                      # upscale small WhatsApp images
        s = 1800 / max(img.size)
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    for angle in (0, 90, 270, 180):
        im = img if angle == 0 else img.rotate(angle, expand=True)
        inv = find_invoice_number(run(im))
        if inv:
            return inv, f"OCR-{name}" + (f"-rot{angle}" if angle else "")
    return None, f"OCR-{name}"


def read_invoice_number(path):
    if path.lower().endswith(".pdf"):
        text, img = pdf_text_and_image(path)
        inv = find_invoice_number(text)
        if inv:
            return inv, "PDF-text"
        if img is None:
            return None, "PDF-no-image"
        return ocr_with_rotations(img)
    with Image.open(path) as im:
        return ocr_with_rotations(im.copy())


# ============================ MAIN =======================================
def unique_target(folder, base, ext):
    target = os.path.join(folder, base + ext)
    n = 2
    while os.path.exists(target):            # second copy of same invoice -> INV-..._2
        target = os.path.join(folder, f"{base}_{n}{ext}")
        n += 1
    return target


def save_as_pdf(src, target, move=False):
    """PDF in -> copied as is. JPG/PNG in -> converted to a 1-page PDF (upright, A4-ish quality)."""
    if src.lower().endswith(".pdf"):
        (shutil.move if move else shutil.copy2)(src, target)
        return
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.save(target, "PDF", resolution=150.0, quality=85)
    if move:
        os.remove(src)


def open_file(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
    except Exception:
        pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prompt = "--no-prompt" not in sys.argv
    move = "--move" in sys.argv
    folder = os.path.abspath(args[0] if args else os.getcwd())
    out_dir = os.path.join(folder, OUTPUT_FOLDER)
    bad_dir = os.path.join(folder, UNMATCHED_FOLDER)
    os.makedirs(out_dir, exist_ok=True)

    files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith(EXTENSIONS) and os.path.isfile(os.path.join(folder, f))
    )
    if not files:
        print(f"No JPG/PNG/PDF files found in {folder}")
        return

    engine = get_engine()[0]
    print(f"\nFolder : {folder}\nFiles  : {len(files)}\nOCR    : {engine} (offline)\n")
    log_rows, ok, manual, failed = [], 0, 0, 0

    for i, f in enumerate(files, 1):
        src = os.path.join(folder, f)
        ext = os.path.splitext(f)[1].lower()
        print(f"[{i}/{len(files)}] {f}")
        try:
            inv, method = read_invoice_number(src)
        except Exception as e:
            inv, method = None, f"ERROR: {e}"

        if not inv and prompt:
            open_file(src)
            typed = input("    Could not read invoice number. Type it (or Enter to skip): ").strip().upper()
            if typed:
                inv, method = typed, "manual"

        if inv:
            target = unique_target(out_dir, inv, ".pdf")
            save_as_pdf(src, target, move)
            status = "RENAMED"
            if method == "manual":
                manual += 1
            else:
                ok += 1
            print(f"    -> {os.path.basename(target)}   ({method})")
        else:
            os.makedirs(bad_dir, exist_ok=True)
            target = os.path.join(bad_dir, f)
            shutil.copy2(src, target)
            status = "NOT FOUND"
            failed += 1
            print(f"    -> NOT FOUND, copied to {UNMATCHED_FOLDER}\\   ({method})")

        log_rows.append([datetime.now().strftime("%d-%m-%Y %H:%M:%S"), f,
                         os.path.basename(target), inv or "", method, status])

    log_path = os.path.join(folder, LOG_FILE)
    new_log = not os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_log:
            w.writerow(["Run time", "Original file", "New file", "Invoice no", "Method", "Status"])
        w.writerows(log_rows)

    print(f"\nDone. Auto-read: {ok} | Typed manually: {manual} | Not found: {failed}")
    print(f"Upload the files in:  {out_dir}")
    print(f"Log saved to:         {log_path}\n")


if __name__ == "__main__":
    main()
