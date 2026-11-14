"""Load both documents and run the comparison."""
import dataclasses
import os

from .comparer import compare_documents
from .extract_docx import extract_docx
from .extract_pdf import Cancelled, extract_image, extract_pdf, extract_txt

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


def _scaled(progress, lo, hi):
    if progress is None:
        return None
    return lambda f, m: progress(lo + (hi - lo) * max(0.0, min(1.0, f)), m)


def load_document(path, options, progress=None, cancel=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        doc = extract_docx(path, options, progress, cancel)
    elif ext == ".pdf":
        doc = extract_pdf(path, options, progress, cancel)
    elif ext in IMAGE_EXT:
        doc = extract_image(path, options, progress, cancel)
    elif ext in (".txt", ".md"):
        doc = extract_txt(path, options, progress, cancel)
    else:
        raise ValueError(f"Unsupported file type: {ext or path}.  Use .docx, .pdf, .txt or a scanned image.")
    for i, b in enumerate(doc.blocks):
        b.idx = i; b.uid = i
    return doc


def run_comparison(path_a, path_b, options, progress=None, cancel=None):
    opt_a = dataclasses.replace(options, pages=None, page_rotation=None)
    if progress:
        progress(0.0, "Reading the draft…")
    da = load_document(path_a, opt_a, _scaled(progress, 0.0, 0.08), cancel)
    db = load_document(path_b, options, _scaled(progress, 0.08, 0.80), cancel)
    if not da.blocks:
        raise ValueError("No text could be read from the draft document.")
    if not db.blocks:
        raise ValueError("No text could be read from the executed copy – check the page selection / OCR language.")
    return compare_documents(da, db, options, _scaled(progress, 0.80, 1.0), cancel)
