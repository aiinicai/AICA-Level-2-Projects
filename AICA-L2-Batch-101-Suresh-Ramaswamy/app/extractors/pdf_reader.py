"""PDF invoice extraction (text PDFs via PyMuPDF; scanned PDFs via optional Tesseract OCR).

All results are heuristic and are always routed to staff review (confidence < 1.0).
OCR works in memory only - no temporary image files are written.
"""
import io
import logging
import re
from decimal import Decimal
from pathlib import Path

from . import ReadResult
from ..gstin import state_of
from ..models import Line
from ..utils import D, parse_date, state_from_text, snap_rate, parse_rates, ZERO

log = logging.getLogger(__name__)

GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
INV_RE = re.compile(r"(?:tax\s*)?invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-_.]{1,24})", re.I)
DATE_RE = re.compile(r"(?:invoice\s*)?date\s*[:\-]?\s*(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|"
                     r"\d{1,2}[\s\-][A-Za-z]{3,9}[\s\-,]*\d{2,4})", re.I)
ANY_DATE_RE = re.compile(r"\b(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\b")
# item table row:  description  HSN  qty  rate  GST%  amount  GST  total
ITEM_RE = re.compile(r"^\s*(?P<desc>.*?\S)\s+(?P<hsn>\d{4,8})\s+(?P<qty>\d[\d,]*(?:\.\d+)?)\s+"
                     r"(?P<rate>\d[\d,]*(?:\.\d+)?)\s+(?P<gst>\d{1,2}(?:\.\d+)?)\s*%\s+"
                     r"(?P<amt>\d[\d,]*(?:\.\d+)?)\s+(?P<tax>\d[\d,]*(?:\.\d+)?)\s+"
                     r"(?P<tot>\d[\d,]*(?:\.\d+)?)\s*$")
AMT_RE = re.compile(r"(-?\d[\d,]*\.\d{1,2})\b")
HSN_RE = re.compile(r"(?:hsn|sac)(?:\s*/\s*sac)?(?:\s*code)?\s*[:\-]?\s*(\d{4,8})", re.I)


def _amount_on_label(text: str, labels) -> Decimal:
    """Last line containing one of labels -> last decimal amount on that line."""
    found = None
    for line in text.splitlines():
        low = re.sub(r"\s+", " ", line.lower())
        if any(lb in low for lb in labels):
            nums = AMT_RE.findall(line)
            if nums:
                found = D(nums[-1])
    return found if found is not None else ZERO


def page_text(page) -> str:
    """Page text with table rows kept on one line (label and value side by side)."""
    try:
        words = page.get_text("words")
    except Exception:  # noqa
        words = []
    if not words:
        return page.get_text()
    return words_to_text(words)


def words_to_text(words) -> str:
    """words: (x0, y0, x1, y1, text, ...) tuples -> text lines ordered top to bottom, left to right."""
    ws = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows, cur, cy = [], [], None
    for w in ws:
        yc = (w[1] + w[3]) / 2
        h = max(w[3] - w[1], 1)
        if cy is None or abs(yc - cy) <= h * 0.5:
            cur.append(w)
            cy = yc if cy is None else (cy + yc) / 2
        else:
            rows.append(cur)
            cur, cy = [w], yc
    if cur:
        rows.append(cur)
    out = []
    for r in rows:
        r.sort(key=lambda w: w[0])
        out.append("  ".join(str(w[4]) for w in r))
    return "\n".join(out)


MAX_OCR_PIXELS = 20_000_000


LAST_OCR_ERROR = ""          # why the last OCR attempt returned nothing (shown in the extract message)
_WIN_TESSERACT = (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")


def _find_tesseract(tesseract_path: str) -> str:
    """The path typed in Settings; else the program on PATH; else the usual Windows install folders."""
    import os
    import shutil
    if tesseract_path:
        return tesseract_path
    if shutil.which("tesseract"):
        return ""
    for c in _WIN_TESSERACT:
        if os.path.exists(c):
            return c
    return ""


def _ocr_page(page, tesseract_path: str) -> str:
    global LAST_OCR_ERROR
    LAST_OCR_ERROR = ""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        LAST_OCR_ERROR = "Python packages pytesseract / pillow are not installed (run: pip install pytesseract pillow)"
        return ""
    tesseract_path = _find_tesseract(tesseract_path)
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    # 300 dpi for a normal page; a very large scanned page (e.g. a phone/scanner image stored as a huge page) is rendered
    # smaller so the picture stays under ~20 million pixels (faster OCR, no Pillow "decompression bomb" warning)
    w, h = max(page.rect.width, 1.0), max(page.rect.height, 1.0)
    dpi = min(300.0, 72.0 * (MAX_OCR_PIXELS / (w * h)) ** 0.5)
    dpi = int(max(dpi, 72.0))                              # PyMuPDF needs a whole number for dpi
    try:
        pix = page.get_pixmap(dpi=dpi)
    except Exception:  # noqa  - another PyMuPDF build: use the zoom form of the same render
        try:
            import pymupdf as _mu
        except ImportError:
            import fitz as _mu
        pix = page.get_pixmap(matrix=_mu.Matrix(dpi / 72.0, dpi / 72.0))
    Image.MAX_IMAGE_PIXELS = None            # size is already capped above; the image came from our own render
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        return pytesseract.image_to_string(img, timeout=180)
    except Exception as e:  # noqa
        log.warning("OCR failed: %s", type(e).__name__)
        if type(e).__name__ == "TesseractNotFoundError":
            LAST_OCR_ERROR = ("the Tesseract program was not found - type its path (for example "
                              "C:\\Program Files\\Tesseract-OCR\\tesseract.exe) in Settings (tab 14), click Save Settings, "
                              "restart the app")
        else:
            LAST_OCR_ERROR = f"{type(e).__name__}: {str(e)[:120]}"
        return ""


def parse_invoice_text(text: str, client: dict, rates, ref: str, source: str) -> Line:
    own = client["gstin"]
    gstins = list(dict.fromkeys(GSTIN_RE.findall(text.upper())))
    others = [g for g in gstins if g != own]
    l = Line(source_file=source, source_ref=ref, supplier_gstin=own,
             supplier_name=client.get("legal_name") or client["name"])
    found = 0
    total_fields = 7
    notes = []
    if own not in gstins:
        notes.append("Client GSTIN not found on document - confirm supplier")
    if others:
        l.recipient_gstin = others[0]
        found += 1
        if len(others) > 1:
            notes.append("Several GSTINs found - confirm recipient")
    m = INV_RE.search(text)
    if m:
        l.invoice_no = m.group(1).strip(".-/")
        found += 1
    m = DATE_RE.search(text) or ANY_DATE_RE.search(text)
    if m:
        l.invoice_date = parse_date(m.group(1))
        found += 1 if l.invoice_date else 0
    cgst = _amount_on_label(text, ["cgst"])
    sgst = _amount_on_label(text, ["sgst", "utgst"])
    igst = _amount_on_label(text, ["igst"])
    l.cgst, l.sgst, l.igst = cgst, sgst, igst
    l.cess = _amount_on_label(text, ["cess"])
    l.taxable = _amount_on_label(text, ["taxable value", "taxable amount", "total taxable", "sub total", "subtotal"])
    l.invoice_total = _amount_on_label(text, ["grand total", "invoice total", "total invoice value",
                                              "total amount", "net amount", "amount payable"])
    if l.taxable:
        found += 1
    if not l.taxable and l.invoice_total:
        l.taxable = l.invoice_total - l.cgst - l.sgst - l.igst - l.cess
        notes.append("Taxable value derived from total minus taxes")
    if l.invoice_total:
        found += 1
    if l.taxable:
        l.rate = snap_rate(l.taxable, l.cgst + l.sgst + l.igst, rates)
        found += 1
    hs = list(dict.fromkeys(HSN_RE.findall(text)))
    if hs:
        l.hsn = hs[0]
        found += 1
        if len(hs) > 1:
            notes.append(f"Multiple HSN found ({', '.join(hs[:4])}) - item split needs manual review")
    pm = re.search(r"place\s*of\s*supply\s*[:\-]?\s*([0-9]{2}[\s\-]*[A-Za-z ]*|[A-Za-z ]{4,30})", text, re.I)
    if pm:
        l.pos = state_from_text(pm.group(1))
    if not l.pos and l.recipient_gstin:
        l.pos = state_of(l.recipient_gstin)
    items = []
    for ln in text.splitlines():
        m = ITEM_RE.match(ln)
        if m:
            items.append(m)
    if items:
        return _lines_from_items(l, items, text, rates, ref, source, found, total_fields, notes)
    l.confidence = round(min(0.8, found / total_fields), 2)
    l.note = "; ".join(["Extracted from PDF - verify all fields"] + notes)
    return l


def _lines_from_items(base: Line, items, text, rates, ref, source, found, total_fields, notes):
    """One Line per item row of the invoice table; GST split CGST+SGST (same state) or IGST."""
    import copy
    if not base.pos and base.recipient_gstin:
        base.pos = state_of(base.recipient_gstin)
    intra = bool(base.pos) and base.pos == (state_of(base.supplier_gstin) or "")
    grand = _amount_on_label(text, ["grand total", "invoice total", "total invoice value",
                                    "total amount", "net amount", "amount payable"])
    out = []
    for m in items:
        l = copy.copy(base)
        l.hsn = m.group("hsn")
        l.description = m.group("desc")
        l.qty = D(m.group("qty").replace(",", ""))
        l.taxable = D(m.group("amt").replace(",", ""))
        tax = D(m.group("tax").replace(",", ""))
        l.rate = snap_rate(l.taxable, tax, rates) if l.taxable else D(m.group("gst"))
        if intra:
            l.cgst = l.sgst = (tax / 2).quantize(Decimal("0.01"))
            l.igst = ZERO
        else:
            l.igst, l.cgst, l.sgst = tax, ZERO, ZERO
        l.cess = ZERO
        l.invoice_total = grand or D(m.group("tot").replace(",", ""))
        f = found + (1 if not base.hsn else 0)
        if not base.taxable:
            f += 1
        if not base.rate:
            f += 1
        if not base.invoice_total and l.invoice_total:
            f += 1
        l.confidence = round(min(0.9, f / total_fields), 2)
        l.note = "; ".join(["Extracted from PDF item table - verify"] + notes)
        l.source_ref = ref
        out.append(l)
    return out


EMBED_PREFIX = "SBDATA1:"


def lines_from_embedded(keywords: str, client: dict, source: str):
    """Smart Billing PDFs carry their own data inside the file; returns (lines, messages) or None."""
    import base64
    import json
    import zlib
    if not keywords or not keywords.startswith(EMBED_PREFIX):
        return None
    try:
        data = json.loads(zlib.decompress(base64.urlsafe_b64decode(keywords[len(EMBED_PREFIX):])).decode("utf-8"))
    except Exception:  # noqa
        return None
    msgs = ["Read from the data stored inside the Smart Billing PDF (exact, not guessed from the layout)"]
    if data.get("seller_gstin") and data["seller_gstin"] != client["gstin"]:
        msgs.append(f"PDF was issued by GSTIN {data['seller_gstin']}, not this client's GSTIN - check the file")
    note = {"Credit Note": "C", "Debit Note": "D"}.get(data.get("type"), "")
    lines = []
    for r in data.get("rows", []):
        l = Line(source_file=source, source_ref="PDF data", supplier_gstin=client["gstin"],
                 supplier_name=client.get("legal_name") or client["name"])
        l.invoice_no = data.get("no", "")
        l.invoice_date = parse_date(data.get("date", ""))
        l.recipient_gstin = (data.get("gstin") or "").strip().upper()
        l.recipient_name = data.get("name", "")
        l.pos = data.get("pos", "")
        l.reverse_charge = "Y" if data.get("rcm") == "Y" else "N"
        l.note_type = note
        l.orig_invoice_no = data.get("orig_no", "")
        l.orig_invoice_date = parse_date(data.get("orig_date", ""))
        l.hsn, l.description, l.uqc = r.get("hsn", ""), r.get("desc", ""), r.get("uqc", "")
        l.qty, l.rate, l.taxable = D(r.get("qty")), D(r.get("rate")), D(r.get("taxable"))
        l.igst, l.cgst, l.sgst = D(r.get("igst")), D(r.get("cgst")), D(r.get("sgst"))
        l.invoice_total = D(data.get("total"))
        sup = r.get("supply", "Taxable")
        l.nil_kind = "" if sup == "Taxable" else sup
        l.confidence = 1.0
        l.note = "From Smart Billing PDF data"
        lines.append(l)
    return lines, msgs


def read_pdf(path: Path, client: dict, settings: dict) -> ReadResult:
    res = ReadResult(kind="pdf")
    try:
        try:
            import pymupdf as fitz  # PyMuPDF, current name
        except ImportError:
            import fitz  # older PyMuPDF
    except ImportError:
        res.messages.append("PyMuPDF not installed - run: pip install pymupdf")
        return res
    rates = parse_rates(settings.get("valid_rates", ""))
    ocr_on = settings.get("ocr_enabled", "1") == "1"
    tess = settings.get("tesseract_path", "")
    try:
        doc = fitz.open(path)
    except Exception as e:  # noqa
        res.messages.append(f"Cannot open PDF: {e}")
        return res
    try:
        emb = lines_from_embedded((doc.metadata or {}).get("keywords", ""), client, Path(path).name)
    except Exception:  # noqa
        emb = None
    if emb:
        doc.close()
        res.lines, res.messages = emb[0], emb[1]
        for i, l in enumerate(res.lines, 1):
            l.id = i
        return res
    texts = []
    ocr_used = False
    for i, page in enumerate(doc):
        t = page_text(page)
        if len(t.strip()) < 30:
            if ocr_on:
                t = _ocr_page(page, tess)
                if t.strip():
                    ocr_used = True
                else:
                    res.messages.append(f"Page {i + 1}: scanned page, OCR gave no text" + (f" - {LAST_OCR_ERROR}" if LAST_OCR_ERROR else " (the page may be blank or too faint)"))
            else:
                res.messages.append(f"Page {i + 1}: scanned page and OCR is disabled")
        texts.append(t)
    doc.close()
    if ocr_used:
        res.messages.append("OCR used - accuracy lower, review carefully")
    page_inv = [(INV_RE.search(t).group(1) if INV_RE.search(t) else None) for t in texts]
    distinct = {x for x in page_inv if x}
    chunks = []
    if len(distinct) > 1:
        chunks = [(f"page {i + 1}", t) for i, t in enumerate(texts) if t.strip()]
    elif any(t.strip() for t in texts):
        chunks = [(f"pages 1-{len(texts)}", "\n".join(texts))]
    for ref, t in chunks:
        got = parse_invoice_text(t, client, rates, ref, Path(path).name)
        for l in (got if isinstance(got, list) else [got]):
            if ocr_used:
                l.confidence = min(l.confidence, 0.5)
            res.lines.append(l)
    for i, l in enumerate(res.lines, 1):
        l.id = i
    if not res.lines:
        res.messages.append("No text could be extracted")
    return res
