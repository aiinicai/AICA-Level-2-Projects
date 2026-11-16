"""Local text extraction: PDF text layer, Word (.docx), plain text, and OCR (Windows built-in OCR
engine, Windows.Media.Ocr) for scanned PDF pages and images. Nothing leaves the computer."""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field

DOC_EXTS = {"pdf", "docx", "txt", "md", "csv"}
IMAGE_EXTS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif", "webp"}
EXTRACTABLE = DOC_EXTS | IMAGE_EXTS
MIN_PAGE_CHARS = 25
MAX_OCR_PAGES = 15
MAX_TEXT_BYTES = 5 * 1024 * 1024


@dataclass
class Extracted:
    status: str                      # ok | ocr | empty | error | unsupported
    method: str = ""
    pages: list[tuple[str, str]] = field(default_factory=list)   # (page_ref, text)
    error: str = ""
    doc_modified: str = ""

    @property
    def text(self) -> str:
        return "\n".join(t for _, t in self.pages)

    def to_json(self) -> str:
        return json.dumps(self.pages)


# ------------------------------------------------------------------------------------- OCR
_ocr_engine = None


def ocr_available() -> bool:
    try:
        return _get_engine() is not None
    except Exception:
        return False


def _get_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from winrt.windows.media.ocr import OcrEngine
        eng = OcrEngine.try_create_from_user_profile_languages()
        if eng is None:
            from winrt.windows.globalization import Language
            eng = OcrEngine.try_create_from_language(Language("en-US"))
        _ocr_engine = eng
    return _ocr_engine


def ocr_image(img) -> str:
    """OCR a PIL image with the Windows OCR engine."""
    from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.storage.streams import DataWriter
    eng = _get_engine()
    if eng is None:
        raise RuntimeError("Windows OCR engine is not available (no OCR language installed)")
    from winrt.windows.media.ocr import OcrEngine
    max_dim = OcrEngine.max_image_dimension
    img = img.convert("RGBA")
    if max(img.size) > max_dim:
        scale = max_dim / max(img.size)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    if min(img.size) < 40:
        img = img.resize((img.width * 3, img.height * 3))
    w = DataWriter()
    w.write_bytes(img.tobytes())
    sb = SoftwareBitmap.create_copy_from_buffer(w.detach_buffer(), BitmapPixelFormat.RGBA8, img.width, img.height,
                                                BitmapAlphaMode.STRAIGHT)

    async def go():
        return await eng.recognize_async(sb)

    res = _run_async(go())
    lines = [ln.text for ln in res.lines]
    return "\n".join(lines)


def _run_async(coro):
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    except RuntimeError:
        return asyncio.run(coro)


# ------------------------------------------------------------------------------ extractors
def extract(path: str, allow_ocr: bool = True) -> Extracted:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    try:
        if ext == "pdf":
            return _pdf(path, allow_ocr)
        if ext == "docx":
            return _docx(path)
        if ext in ("txt", "md", "csv"):
            with open(path, "rb") as f:
                data = f.read(MAX_TEXT_BYTES)
            for enc in ("utf-8-sig", "utf-16", "cp1252"):
                try:
                    t = data.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                t = data.decode("latin-1", "replace")
            return Extracted("ok" if t.strip() else "empty", "Text file", [("Line 1", t)])
        if ext in IMAGE_EXTS:
            if not allow_ocr:
                return Extracted("unsupported", "OCR disabled")
            from PIL import Image
            with Image.open(path) as im:
                im.load()
                t = ocr_image(im)
            return Extracted("ocr" if t.strip() else "empty", "OCR (image)", [("Image", t)])
        return Extracted("unsupported", "")
    except Exception as e:  # unreadable / encrypted / corrupt
        return Extracted("error", "", [], f"{type(e).__name__}: {e}")


def _pdf(path: str, allow_ocr: bool) -> Extracted:
    from pypdf import PdfReader
    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            return Extracted("error", "", [], "Password-protected PDF")
    pages = []
    weak = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages.append([f"Page {i + 1}", t])
        if len(re.sub(r"\s", "", t)) < MIN_PAGE_CHARS:
            weak.append(i)
    mod = ""
    try:
        md = reader.metadata
        if md is not None:
            d = md.modification_date or md.creation_date
            if d:
                mod = d.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    used_ocr = False
    if weak and allow_ocr:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(path)
        try:
            for i in weak[:MAX_OCR_PAGES]:
                pil = doc[i].render(scale=200 / 72).to_pil()
                t = ocr_image(pil)
                if t.strip():
                    pages[i][1] = t
                    pages[i][0] = f"Page {i + 1} (OCR)"
                    used_ocr = True
        finally:
            doc.close()
    pages_t = [(a, b) for a, b in pages]
    has_text = any(b.strip() for _, b in pages_t)
    if not has_text:
        return Extracted("empty", "PDF (no readable text)", pages_t, "", mod)
    return Extracted("ocr" if used_ocr else "ok", "PDF text + OCR" if used_ocr else "PDF text layer", pages_t, "", mod)


def _docx(path: str) -> Extracted:
    import docx
    d = docx.Document(path)
    pages = []
    n = 0
    for p in d.paragraphs:
        n += 1
        if p.text.strip():
            pages.append((f"Paragraph {n}", p.text))
    for ti, tbl in enumerate(d.tables):
        for ri, row in enumerate(tbl.rows):
            cells = " | ".join(c.text for c in row.cells)
            if cells.strip(" |"):
                pages.append((f"Table {ti + 1}, row {ri + 1}", cells))
    for si, sec in enumerate(d.sections):
        for part, label in ((sec.header, "Header"), (sec.footer, "Footer")):
            try:
                t = "\n".join(p.text for p in part.paragraphs if p.text.strip())
                if t:
                    pages.append((f"{label} (section {si + 1})", t))
            except Exception:
                pass
    mod = ""
    try:
        cp = d.core_properties
        dt = cp.modified or cp.created
        if dt:
            mod = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return Extracted("ok" if pages else "empty", "Word document", pages, "", mod)


# ------------------------------------------------------------------------------ cache
def cached_extract(db, rel_path: str, allow_ocr=True) -> Extracted:
    full = os.path.join(db.project.root_path, rel_path)
    st = os.stat(full)
    r = db.con.execute("SELECT * FROM doc_text WHERE rel_path=?", (rel_path,)).fetchone()
    if r and r["size"] == st.st_size and r["mtime"] == st.st_mtime and r["status"] != "error":
        return Extracted(r["status"], r["method"] or "", [tuple(x) for x in json.loads(r["pages"] or "[]")],
                         r["error"] or "", r["doc_modified"] or "")
    ex = extract(full, allow_ocr)
    with db._write_lock:
        db.con.execute("INSERT OR REPLACE INTO doc_text(rel_path,size,mtime,status,method,pages,error,doc_modified) "
                       "VALUES(?,?,?,?,?,?,?,?)", (rel_path, st.st_size, st.st_mtime, ex.status, ex.method,
                                                   ex.to_json(), ex.error, ex.doc_modified))
        db.con.commit()
    return ex
