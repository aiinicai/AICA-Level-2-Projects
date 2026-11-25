"""Module 2 — text & table extraction, fully local.

PDF   : pdfplumber (text + tables); falls back to OCR (pdf2image + Tesseract)
        for pages with no text layer (scanned PDFs).
DOCX  : python-docx (paragraphs + tables).
XLSX  : openpyxl (every sheet as a table; formulas read as cached values).
CSV/TXT: decoded text; CSV also parsed as a table.
Images: Tesseract OCR.

Every result carries a status and notes so that the user knows when text is
incomplete (e.g. low OCR confidence) — never silently treated as complete.
"""
from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass, field

from ..core.errors import ExtractionError
from ..core.logging_setup import get_logger

log = get_logger("extraction")
MIN_TEXT_CHARS_PER_PAGE = 25
MAX_OCR_PAGES = 60


@dataclass
class Extracted:
    text: str
    tables: list[dict] = field(default_factory=list)  # {"name": str, "rows": [[...]]}
    status: str = "OK"  # OK, OCR, PARTIAL, FAILED
    notes: list[str] = field(default_factory=list)
    page_count: int | None = None
    # V3: one record per page -> {"page", "method": TEXT|OCR|NONE, "chars", "confidence", "status": OK|LOW_CONFIDENCE|BLANK|FAILED}
    pages: list[dict] = field(default_factory=list)


LOW_CONFIDENCE = 70.0


# ----------------------------------------------------------------- OCR health
def _configure_tesseract():
    import pytesseract

    cmd = os.getenv("TESSERACT_CMD", "").strip().strip('"')
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract, cmd


def _poppler_path() -> str | None:
    p = os.getenv("POPPLER_PATH", "").strip().strip('"')
    return p or None


def ocr_health(run_self_test: bool = True) -> dict:
    """Check each OCR component separately and explain any failure in plain words.

    Returns {"status": READY|DEGRADED|UNAVAILABLE, "tesseract": {...}, "poppler": {...},
             "self_test": {...}, "fixes": [str]}. Contains paths only (never secrets).
    """
    import shutil

    fixes: list[str] = []
    tess: dict = {"configured_path": None, "found": False, "version": None, "languages": [], "eng_available": False, "error": None}
    try:
        pytesseract, cmd = _configure_tesseract()
        tess["configured_path"] = cmd or "(not set; using PATH)"
        if cmd and not os.path.isfile(cmd):
            tess["error"] = "TESSERACT_CMD points to a file that does not exist."
            fixes.append("Open .env and set TESSERACT_CMD to the full path of tesseract.exe "
                         "(usually C:\\Program Files\\Tesseract-OCR\\tesseract.exe).")
        else:
            tess["version"] = str(pytesseract.get_tesseract_version())
            tess["found"] = True
            try:
                tess["languages"] = sorted(pytesseract.get_languages(config=""))
            except Exception:
                tess["languages"] = []
            tess["eng_available"] = "eng" in tess["languages"]
            if not tess["eng_available"]:
                tess["error"] = "Tesseract runs but English language data (eng.traineddata) was not found."
                fixes.append("Reinstall Tesseract and keep 'English' ticked, or copy eng.traineddata into the tessdata folder.")
    except ImportError:
        tess["error"] = "Python package pytesseract is not installed."
        fixes.append("Run: pip install -r requirements.txt")
    except Exception as exc:
        tess["error"] = f"Tesseract could not be started ({type(exc).__name__})."
        fixes.append("Install Tesseract (UB-Mannheim build) and set TESSERACT_CMD in .env to tesseract.exe.")

    pop: dict = {"configured_path": None, "pdftoppm_found": False, "pdfinfo_found": False, "error": None}
    pp = _poppler_path()
    pop["configured_path"] = pp or "(not set; using PATH)"
    exe = ".exe" if os.name == "nt" else ""
    if pp:
        if not os.path.isdir(pp):
            pop["error"] = "POPPLER_PATH points to a folder that does not exist."
            fixes.append("Open .env and set POPPLER_PATH to Poppler's 'Library\\bin' folder (it contains pdftoppm.exe).")
        pop["pdftoppm_found"] = os.path.isfile(os.path.join(pp, "pdftoppm" + exe))
        pop["pdfinfo_found"] = os.path.isfile(os.path.join(pp, "pdfinfo" + exe))
    else:
        pop["pdftoppm_found"] = shutil.which("pdftoppm") is not None
        pop["pdfinfo_found"] = shutil.which("pdfinfo") is not None
    if not pop["error"] and not (pop["pdftoppm_found"] and pop["pdfinfo_found"]):
        pop["error"] = "pdftoppm / pdfinfo were not found, so scanned PDF pages cannot be turned into images."
        fixes.append("Set POPPLER_PATH in .env to the Poppler folder that contains pdftoppm.exe and pdfinfo.exe.")

    st: dict = {"ran": False, "ok": False, "chars": 0, "confidence": None, "error": None}
    if run_self_test and tess["found"] and tess["eng_available"]:
        st["ran"] = True
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("L", (900, 160), 255)
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 48)
            except Exception:
                try:
                    font = ImageFont.truetype("arial.ttf", 48)
                except Exception:
                    font = ImageFont.load_default()
            d.text((30, 50), "NOTICE MATE 143 TEST", fill=0, font=font)
            text, conf = _ocr_image(img)
            st["chars"] = len(text.strip())
            st["confidence"] = round(conf, 1)
            st["ok"] = "NOTICE" in text.upper() or "143" in text
            if not st["ok"]:
                st["error"] = "Tesseract ran but could not read a clear test image."
                fixes.append("Tesseract installation looks damaged. Reinstall it, then re-run the OCR check.")
        except Exception as exc:
            st["error"] = f"Self-test failed ({type(exc).__name__})."

    tess_ok = tess["found"] and tess["eng_available"] and (st["ok"] or not st["ran"])
    pop_ok = pop["pdftoppm_found"] and pop["pdfinfo_found"] and not pop["error"]
    status = "READY" if (tess_ok and pop_ok) else ("DEGRADED" if tess_ok else "UNAVAILABLE")
    if status == "DEGRADED":
        fixes.append("Images can be read, but scanned PDFs cannot until Poppler is fixed.")
    return {"status": status, "tesseract": tess, "poppler": pop, "self_test": st, "fixes": fixes}


def _ocr_available() -> bool:
    try:
        pytesseract, _ = _configure_tesseract()
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_image(img) -> tuple[str, float]:
    pytesseract, _ = _configure_tesseract()
    data = pytesseract.image_to_data(img, lang="eng", output_type=pytesseract.Output.DICT)
    confs = []
    for c, w in zip(data.get("conf", []), data.get("text", [])):
        try:
            cf = float(c)
        except (TypeError, ValueError):
            continue
        if str(w).strip() and cf >= 0:
            confs.append(cf)
    text = pytesseract.image_to_string(img, lang="eng")
    return text, (sum(confs) / len(confs)) if confs else 0.0


def _finalise(ex: Extracted) -> Extracted:
    """Never let an empty or partly-read document look complete."""
    total = len((ex.text or "").replace("\f", "").strip())
    if total == 0:
        ex.status = "FAILED"
        ex.notes.append("NO TEXT WAS EXTRACTED. Nothing in this file can be analysed automatically. "
                        "Run the OCR check, or re-scan the document at 300 dpi.")
    elif ex.status == "PARTIAL":
        bad = [p["page"] for p in ex.pages if p.get("status") in ("BLANK", "FAILED")]
        if bad:
            ex.notes.append(f"PARTIAL EXTRACTION: page(s) {bad} could not be read. Treat the text as incomplete.")
    return ex


def extract_pdf(data: bytes) -> Extracted:
    import pdfplumber

    texts, tables, notes, pages = [], [], [], []
    ocr_pages: list[int] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            n = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                t = page.extract_text() or ""
                if len(t.strip()) < MIN_TEXT_CHARS_PER_PAGE:
                    ocr_pages.append(i)
                texts.append(t)
                pages.append({"page": i, "method": "TEXT", "chars": len(t.strip()), "confidence": None, "status": "OK"})
                try:
                    for j, tb in enumerate(page.extract_tables() or [], 1):
                        if tb and len(tb) > 1:
                            tables.append({"name": f"page{i}_table{j}", "rows": [[(c or "").strip() for c in row] for row in tb]})
                except Exception:
                    notes.append(f"Table extraction failed on page {i}.")
    except Exception as exc:
        raise ExtractionError(f"Could not read PDF: {type(exc).__name__}. The file may be corrupt or password-protected.")

    status = "OK"
    if ocr_pages:
        if not _ocr_available():
            status = "PARTIAL"
            for pno in ocr_pages:
                pages[pno - 1].update(method="NONE", status="BLANK" if pages[pno - 1]["chars"] == 0 else "OK")
            notes.append(f"Page(s) {ocr_pages} have no text layer and Tesseract OCR is not available. Run the OCR check.")
        else:
            from pdf2image import convert_from_bytes

            status = "OCR"
            poppler_error = False
            for pno in ocr_pages[:MAX_OCR_PAGES]:
                rec = pages[pno - 1]
                try:
                    img = convert_from_bytes(data, dpi=300, first_page=pno, last_page=pno, poppler_path=_poppler_path())[0]
                    t, conf = _ocr_image(img)
                    texts[pno - 1] = t
                    rec.update(method="OCR", chars=len(t.strip()), confidence=round(conf, 1))
                    if not t.strip():
                        status = "PARTIAL"
                        rec["status"] = "BLANK"
                        notes.append(f"Page {pno}: OCR returned no readable text.")
                    elif conf < LOW_CONFIDENCE:
                        rec["status"] = "LOW_CONFIDENCE"
                        notes.append(f"Page {pno}: low OCR confidence ({conf:.0f}%). Verify figures against the original.")
                except Exception as exc:
                    status = "PARTIAL"
                    rec.update(method="OCR", status="FAILED")
                    name = type(exc).__name__
                    if "PDFInfo" in name or "Poppler" in name or "PDFPageCount" in name:
                        poppler_error = True
                    notes.append(f"Page {pno}: OCR failed ({name}).")
            if poppler_error:
                notes.append("Poppler (pdftoppm/pdfinfo) could not be run. Check POPPLER_PATH in .env and run the OCR check.")
            if len(ocr_pages) > MAX_OCR_PAGES:
                status = "PARTIAL"
                for pno in ocr_pages[MAX_OCR_PAGES:]:
                    pages[pno - 1].update(method="NONE", status="BLANK")
                notes.append(f"OCR limited to the first {MAX_OCR_PAGES} scanned pages.")
            notes.append("OCR text may contain recognition errors; amounts and dates REQUIRE VERIFICATION against the original.")
    return _finalise(Extracted("\n\f\n".join(texts), tables, status, notes, n, pages))


def extract_docx(data: bytes) -> Extracted:
    import docx

    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read DOCX: {type(exc).__name__}.")
    paras = [p.text for p in d.paragraphs]
    tables = []
    for i, t in enumerate(d.tables, 1):
        rows = [[c.text.strip() for c in r.cells] for r in t.rows]
        tables.append({"name": f"table{i}", "rows": rows})
        paras.append("\n".join(" | ".join(r) for r in rows))
    return Extracted("\n".join(paras), tables, "OK", [], None)


def extract_xlsx(data: bytes) -> Extracted:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception as exc:
        raise ExtractionError(f"Could not read XLSX: {type(exc).__name__}.")
    tables, lines, notes = [], [], []
    for ws in wb.worksheets:
        rows = []
        for r in ws.iter_rows(values_only=True):
            if r is None or all(v is None or str(v).strip() == "" for v in r):
                continue
            rows.append(["" if v is None else (v.strftime("%d-%m-%Y") if hasattr(v, "strftime") else str(v)) for v in r])
        if rows:
            tables.append({"name": ws.title, "rows": rows})
            lines.append(f"## Sheet: {ws.title}")
            lines.extend(" | ".join(r) for r in rows)
    wb.close()
    notes.append("Formula cells are read as last-saved values; if the workbook was never recalculated, values may be blank.")
    return Extracted("\n".join(lines), tables, "OK", notes, None)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("Unsupported text encoding.")


def extract_csv(data: bytes) -> Extracted:
    text = _decode(data)
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    return Extracted(text, [{"name": "csv", "rows": rows}], "OK", [], None)


def extract_image(data: bytes) -> Extracted:
    if not _ocr_available():
        return Extracted("", [], "FAILED", ["OCR (Tesseract) not available; image not readable. Run the OCR check."], 1,
                         [{"page": 1, "method": "NONE", "chars": 0, "confidence": None, "status": "FAILED"}])
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    t, conf = _ocr_image(img)
    notes = ["OCR text — amounts and dates REQUIRE VERIFICATION against the original."]
    pstat = "OK"
    status = "OCR"
    if not t.strip():
        pstat, status = "BLANK", "PARTIAL"
    elif conf < LOW_CONFIDENCE:
        pstat = "LOW_CONFIDENCE"
        notes.append(f"Low OCR confidence ({conf:.0f}%).")
    return _finalise(Extracted(t, [], status, notes, 1,
                               [{"page": 1, "method": "OCR", "chars": len(t.strip()), "confidence": round(conf, 1), "status": pstat}]))


def extract(ext: str, data: bytes) -> Extracted:
    ext = ext.lower()
    try:
        if ext == ".pdf":
            return extract_pdf(data)
        if ext == ".docx":
            return extract_docx(data)
        if ext in (".xlsx", ".xlsm"):
            return extract_xlsx(data)
        if ext == ".csv":
            return extract_csv(data)
        if ext == ".txt":
            return Extracted(_decode(data), [], "OK", [], None)
        if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            return extract_image(data)
    except ExtractionError:
        raise
    except Exception as exc:  # defensive: never crash the upload pipeline
        log.exception("extraction failure")
        return Extracted("", [], "FAILED", [f"Extraction error: {type(exc).__name__}"], None)
    raise ExtractionError(f"Unsupported extension {ext}")
