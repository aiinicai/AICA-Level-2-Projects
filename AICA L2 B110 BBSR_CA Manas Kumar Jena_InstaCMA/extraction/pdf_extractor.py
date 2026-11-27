"""
PDF / image extractor.

Searchable PDFs are read with pdfplumber; pages with little or no text are
sent to the OCR engine.  Each text line is split into segments
(label followed by amounts) so that T-form statements, where liabilities and
assets (or expenses and income) sit side by side on one line, give two lines.
When a page header shows two years (current and previous year columns), the
amounts in a segment are assigned to those years in header order.
"""
import os
import re

from core.models import SourceLine
from extraction.statement_detector import (parse_amount, is_amount_token, classify_text,
                                           detect_years)
from extraction import ocr_engine

_SPLIT = re.compile(r"\s+")


def split_segments(line):
    """'To Rent 2,40,000 By Sales 1,00,000' -> [('To Rent',[240000]), ('By Sales',[100000])]."""
    toks = _SPLIT.split(line.strip())
    segs, label, nums = [], [], []
    for t in toks:
        if is_amount_token(t) and label:
            v = parse_amount(t)
            if v is not None:
                nums.append(v)
                continue
        if nums:
            segs.append((" ".join(label), nums))
            label, nums = [], []
        label.append(t)
    if label:
        segs.append((" ".join(label), nums))
    clean = []
    for lab, ns in segs:
        lab = lab.strip(" .:-")
        low = lab.lower()
        if any(w in low for w in ("year ended", "as at", "as on", "period ended", "page ")):
            continue
        if lab and ns and re.search(r"[A-Za-z]", lab):
            clean.append((lab, ns))
    return clean


def _page_texts(path, use_ocr=True, log=None):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            if len(re.sub(r"\s", "", txt)) < 40 and use_ocr:
                if ocr_engine.tesseract_available():
                    if log:
                        log("Page %d: scanned image - running OCR" % (i + 1))
                    txt = ocr_engine.ocr_pdf_page(path, i)
                elif log:
                    log("Page %d: scanned image but Tesseract is not installed - page skipped" % (i + 1))
            yield i, txt


def lines_from_text(text, src, default_year=None, force_statement=None, current_statement=""):
    from extraction.tform_rules import TState, emit
    st = force_statement or classify_text(text) or current_statement
    years = detect_years(text[:1500])
    out = []
    state = TState()
    for raw in text.splitlines():
        low = raw.lower()
        if "balance sheet" in low and not force_statement:
            st = "BS"
        elif ("profit and loss" in low or "profit & loss" in low or "trading account" in low
              or "income and expenditure" in low) and not force_statement:
            st = "PL"
        for side, (lab, nums) in enumerate(split_segments(raw)):
            if len(years) < 2:
                y = years[0] if years else default_year
                if y is not None:
                    out += emit(state, side, lab, nums, y, st or "PL", src)
                continue
            if len(years) >= 2 and len(nums) >= 2:
                for y, n in zip(years, nums[-len(years):]):
                    out.append(SourceLine(year=y, statement=st or "PL", label=lab, amount=n, source=src))
            else:
                y = years[0] if years else default_year
                if y is None:
                    continue
                out.append(SourceLine(year=y, statement=st or "PL", label=lab, amount=nums[-1], source=src))
    return out, st


def extract_pdf(path, default_year=None, force_statement=None, use_ocr=True):
    lines, info = [], []
    base = os.path.basename(path)
    st = ""
    for i, txt in _page_texts(path, use_ocr, log=info.append):
        src = "%s / page %d" % (base, i + 1)
        ls, st = lines_from_text(txt, src, default_year, force_statement, st)
        if not ls and not detect_years(txt) and default_year is None:
            info.append("%s: financial year not found - choose it on the Upload page." % src)
        lines += ls
        info.append("%s: %s, %d lines." % (src, st or "?", len(ls)))
    return lines, info


def extract_image(path, default_year=None, force_statement=None):
    if not ocr_engine.tesseract_available():
        return [], ["Tesseract OCR is not installed; images cannot be read. See Settings."]
    txt = ocr_engine.ocr_image_file(path)
    ls, st = lines_from_text(txt, os.path.basename(path), default_year, force_statement)
    return ls, ["%s: OCR read, %s, %d lines." % (os.path.basename(path), st or "?", len(ls))]


def extract_any(path, default_year=None, force_statement=None):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        from extraction.excel_extractor import extract_excel
        return extract_excel(path, default_year, force_statement)
    if ext == ".pdf":
        return extract_pdf(path, default_year, force_statement)
    if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        return extract_image(path, default_year, force_statement)
    return [], ["Unsupported file type: %s" % ext]
