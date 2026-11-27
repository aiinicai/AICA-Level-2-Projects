"""
Reading pipeline: files -> raw lines -> CMA heads -> Trading / P&L section.

  Excel        read directly (any layout, or the CMA Input Template)
  PDF / photo  AI reading when an AI provider is set (any model), page by page;
               otherwise text extraction + OCR for scanned pages
Heads come from your saved remaps first, then the keyword rules, then (if an
AI provider is set) an AI suggestion for anything still unplaced.
"""
import os
import re

from analysis.mapper import map_lines
from config.constants import HEAD_LABEL
from core.audit_trail import TRAIL
from extraction import pdf_extractor, excel_extractor, ocr_engine

GP = re.compile(r"gross\s+profit|gross\s+loss", re.I)
ALLOWED = [(k, v) for k, v in HEAD_LABEL.items()] + [("ignore", "total / heading / not an item"),
                                                     ("_reported_net_profit", "net profit as reported")]


def _ai_pdf(path, settings, log):
    from ai.extract import read_page
    import pdfplumber
    out = []
    base = os.path.basename(path)
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            img = None
            if len(re.sub(r"\s", "", text)) < 200:
                for _, im in ocr_engine.render_pdf_pages(path, [i], scale=2.0):
                    import io
                    buf = io.BytesIO()
                    im.save(buf, format="PNG")
                    img = buf.getvalue()
            src = "%s / page %d" % (base, i + 1)
            lines = read_page(settings, text, img, src)
            log("%s: AI read %d values%s." % (src, len(lines), " (scanned page sent as image)" if img else ""))
            out += lines
    return out


def _ai_image(path, settings, log):
    from ai.extract import read_page
    with open(path, "rb") as fh:
        raw = fh.read()
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    lines = read_page(settings, "", buf.getvalue(), os.path.basename(path))
    log("%s: AI read %d values." % (os.path.basename(path), len(lines)))
    return lines


def set_sections(lines):
    """P&L expense lines before a 'Gross Profit' line are Trading; after it, Profit & Loss."""
    groups = {}
    for ln in lines:
        if ln.statement == "PL":
            groups.setdefault((ln.source.split(" / page")[0].split(" / ")[0], ln.year), []).append(ln)
    for _, grp in groups.items():
        if not any(GP.search(ln.label) for ln in grp):
            continue
        sec = "trading"
        for ln in grp:
            if GP.search(ln.label):
                sec = "pl"
                continue
            if not ln.section:
                ln.section = sec


def read_files(paths, settings, use_ai=True, default_year=None, force_statement=None, log=print):
    from ai.providers import ai_enabled, AIError
    ai_on = use_ai and ai_enabled(settings)
    allout = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        lines = []
        try:
            if ext in (".xlsx", ".xls", ".xlsm"):
                lines, info = excel_extractor.extract_excel(p, default_year, force_statement)
                for m in info:
                    log(m)
            elif ai_on and ext == ".pdf":
                try:
                    lines = _ai_pdf(p, settings, log)
                except AIError as e:
                    log("AI reading failed (%s) - using text / OCR reading instead." % e)
                    lines, info = pdf_extractor.extract_pdf(p, default_year, force_statement)
                    for m in info:
                        log(m)
            elif ai_on and ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
                try:
                    lines = _ai_image(p, settings, log)
                except AIError as e:
                    log("AI reading failed (%s) - using OCR instead." % e)
                    lines, info = pdf_extractor.extract_image(p, default_year, force_statement)
                    for m in info:
                        log(m)
            else:
                lines, info = pdf_extractor.extract_any(p, default_year, force_statement)
                for m in info:
                    log(m)
        except Exception as e:
            log("%s: could not be read (%s)" % (os.path.basename(p), e))
        TRAIL.log("File read", "%s - %d values" % (os.path.basename(p), len(lines)))
        allout += lines
    set_sections(allout)
    map_lines(allout)
    for ln in allout:            # an expense head on the income (Cr) side of a T-form P&L is other income
        if ln.statement == "PL" and ln.side == 1 and ln.head not in ("sales", "closing_stock", "other_income",
                                                                      "ignore", "_reported_net_profit", ""):
            ln.head, ln.note = "other_income", "income side of the P&L"
    if ai_on:
        try:
            from ai.extract import suggest_heads
            n = suggest_heads(settings, allout, ALLOWED)
            if n:
                log("AI suggested heads for %d line(s) - please check them on the Review page." % n)
        except Exception as e:
            log("AI head suggestion skipped (%s)." % e)
    return allout
