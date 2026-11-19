"""Read any invoice file into text + page images, using only pure-Python libraries
(pypdf, openpyxl, zipfile) and Qt for images, so Smart App Control has nothing to block.
pypdfium2 / Pillow are used only if present and allowed."""
from __future__ import annotations

import hashlib
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

PDF = {".pdf"}
IMAGES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
WORD = {".docx", ".doc"}
EXCEL = {".xlsx", ".xlsm", ".xls", ".csv"}
SUPPORTED = PDF | IMAGES | WORD | EXCEL


@dataclass
class Document:
    path: Path
    kind: str                                   # pdf | image | docx | xlsx
    text: str = ""
    page_images: list[bytes] = field(default_factory=list)   # PNG/JPEG/TIFF bytes, one per page
    pages: int = 1
    has_text_layer: bool = False
    pdf_bytes: bytes = b""


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path: Path) -> Document:
    path = Path(path)
    ext = path.suffix.lower()
    if ext in PDF:
        return read_pdf(path)
    if ext in IMAGES:
        return Document(path, "image", page_images=[path.read_bytes()])
    if ext == ".docx":
        return Document(path, "docx", text=read_docx(path), has_text_layer=True)
    if ext == ".doc":
        converted = _libreoffice_convert(path, "docx")
        if converted:
            return Document(path, "docx", text=read_docx(converted), has_text_layer=True)
        raise ValueError("Legacy .doc needs LibreOffice installed (or save it as .docx / PDF).")
    if ext in EXCEL:
        return Document(path, "xlsx", text=read_sheet(path), has_text_layer=True)
    raise ValueError(f"Unsupported file type: {ext}")


# ------------------------------------------------------------------ PDF
_SPLIT_NUM = re.compile(r"(?<![\w.,])(\d[\d,]*) (\d[\d,]*(?:\.\d+)?)(?![\w,]|\.\d)")
# a complete amount: Indian 2,78,645.00 / international 278,645.00 / plain 278645.00
_WELL_FORMED = re.compile(r"^(?:\d{1,2}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,3})?$")
# split just before a comma or decimal point: '2 ,78,645.00', '2,78,645 .00' (a fragment starting with ',' or
# '.' is never a number on its own)
_SPLIT_PUNCT = re.compile(r"(?<![\w.,])(\d[\d,]*) ([.,]\d[\d,]*(?:\.\d+)?)(?![\w,]|\.\d)")
# a digit segment of a reference broken by one space: 'SKP/112 5/2 6-2 7' -> 'SKP/1125/26-27'
_SPLIT_REF = re.compile(r"(?<=[/\-])(\d{1,6}) (\d{1,3})(?=[/\-]|\s{2,}|\s*$)")
# a run of number pieces separated by single spaces: '2 1,2 52.60' -> '21,252.60' (columns are wider apart)
_SPLIT_CHAIN = re.compile(r"(?<![\w.,])\d[\d,.]*(?: [\d,.]*\d[\d,.]*)+(?![\w,])")
# GSTIN broken by single spaces: '2 4ABCPS12 34K1ZS' -> '24ABCPS1234K1ZS'
_SPLIT_GSTIN = re.compile(r"(?<![0-9A-Z])" + " ?".join([r"\d", r"\d"] + ["[A-Z]"] * 5 + [r"\d"] * 4 +
                                                      ["[A-Z]", "[1-9A-Z]", "Z", "[0-9A-Z]"]) + r"(?![0-9A-Z])")
_SPLIT_SLASH = re.compile(r"(?<=\w) (?=[/\-]\w)|(?<=\w[/\-]) (?=\w)")


def heal_pdf_text(t: str) -> str:
    """PDF text layers often split one token across glyph runs: '21,25 2.60', 'RRA/1125 /26-27'.
    Re-join a split only when the result is a well-formed number / reference."""
    t = t.replace("\t", " ")
    out = []
    for line in t.splitlines():
        line = _SPLIT_SLASH.sub("", line)
        line = _SPLIT_GSTIN.sub(lambda m: m.group(0).replace(" ", ""), line)
        prev = None
        while prev != line:
            prev, line = line, _SPLIT_REF.sub(lambda m: m.group(1) + m.group(2), line)
        # dates broken inside the year: '01-11-2 02 6' -> '01-11-2026'
        line = re.sub(r"\b(\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3})[-/.])(\d) ?(\d) ?(\d) ?(\d)\b",
                      lambda m: m.group(1) + "".join(m.group(i) for i in range(2, 6)), line)

        def chain(m):
            parts = m.group(0).split(" ")
            whole = "".join(parts)
            if any(not _WELL_FORMED.match(p) for p in parts) and _WELL_FORMED.match(whole) and \
                    re.search(r"[,.]", whole):
                return whole
            return m.group(0)
        line = _SPLIT_CHAIN.sub(chain, line)

        def join(m):
            a, b = m.group(1), m.group(2)
            if _WELL_FORMED.match(a + b) and "," in a and not _WELL_FORMED.match(a):
                return a + b                   # '21,25' + '2.60' -> '21,252.60'
            return m.group(0)
        prev = None
        while prev != line:
            prev, line = line, _SPLIT_NUM.sub(join, line)
            line = _SPLIT_PUNCT.sub(lambda m: m.group(1) + m.group(2) if _WELL_FORMED.match(m.group(1) + m.group(2))
                                    else m.group(0), line)
        out.append(line)
    return "\n".join(out)


def read_pdf(path: Path) -> Document:
    from pypdf import PdfReader
    data = path.read_bytes()
    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise ValueError("PDF is password protected") from e
    texts = []
    for page in reader.pages:
        try:
            t = page.extract_text(extraction_mode="layout") or ""
        except Exception:
            t = page.extract_text() or ""
        texts.append(heal_pdf_text(t))
    text = "\n\f\n".join(texts)
    has_text = sum(len(t.strip()) for t in texts) > 80
    doc = Document(path, "pdf", text=text, pages=len(reader.pages), has_text_layer=has_text, pdf_bytes=data)
    doc.page_images = render_pdf(path, reader) if not has_text else []
    return doc


def render_pdf(path: Path, reader=None, dpi: int = 200) -> list[bytes]:
    """Page images. pypdfium2 if available; else the scanned image embedded in each page."""
    try:
        import pypdfium2 as pdfium          # optional native renderer
        pdf = pdfium.PdfDocument(str(path))
        out = []
        for i in range(len(pdf)):
            img = pdf[i].render(scale=dpi / 72).to_pil()
            import io
            buf = io.BytesIO()
            img.save(buf, "PNG")
            out.append(buf.getvalue())
        return out
    except Exception:
        pass
    from .ocr import windows_render_pdf          # Windows' own PDF renderer via PowerShell
    pages = windows_render_pdf(path, max_pages=3, dpi=dpi)
    if pages:
        return pages
    from pypdf import PdfReader
    reader = reader or PdfReader(path)
    out = []
    for page in reader.pages:
        img = _largest_embedded_image(page)
        if img:
            out.append(img)
    return out


def _largest_embedded_image(page) -> bytes | None:
    try:
        xobjs = page["/Resources"]["/XObject"].get_object()
    except Exception:
        return None
    best, best_area = None, 0
    for name in xobjs:
        x = xobjs[name].get_object()
        if x.get("/Subtype") != "/Image":
            continue
        w, h = int(x.get("/Width", 0)), int(x.get("/Height", 0))
        if w * h <= best_area:
            continue
        img = _xobject_to_bytes(x, w, h)
        if img:
            best, best_area = img, w * h
    return best


def _xobject_to_bytes(x, w: int, h: int) -> bytes | None:
    filters = x.get("/Filter")
    filters = [str(f) for f in filters] if isinstance(filters, list) else [str(filters)] if filters else []
    try:
        if "/DCTDecode" in filters:
            return x._data                                   # already a JPEG
        if "/CCITTFaxDecode" in filters:
            parms = x.get("/DecodeParms") or {}
            if isinstance(parms, list):
                parms = parms[0] or {}
            k = int(parms.get("/K", 0))
            black1 = bool(parms.get("/BlackIs1", False))
            return _ccitt_to_tiff(x._data, w, h, k, black1)
        data = x.get_data()                                  # Flate etc. decoded by pypdf (pure Python)
        bpc = int(x.get("/BitsPerComponent", 8))
        cs = str(x.get("/ColorSpace", "/DeviceRGB"))
        return _raw_to_png(data, w, h, bpc, cs)
    except Exception:
        return None


def _ccitt_to_tiff(data: bytes, w: int, h: int, k: int, black_is_1: bool) -> bytes:
    """Wrap raw CCITT G3/G4 data in a minimal TIFF so Qt can decode it."""
    compression = 4 if k < 0 else 3
    photometric = 1 if black_is_1 else 0
    tags = [(256, 4, 1, w), (257, 4, 1, h), (258, 3, 1, 1), (259, 3, 1, compression),
            (262, 3, 1, photometric), (273, 4, 1, 0), (277, 3, 1, 1), (278, 4, 1, h),
            (279, 4, 1, len(data))]
    if compression == 3:
        tags.append((292, 4, 1, 0))
    tags.sort()
    ifd_offset = 8
    ifd_size = 2 + 12 * len(tags) + 4
    data_offset = ifd_offset + ifd_size
    out = bytearray(b"II*\x00" + struct.pack("<I", ifd_offset))
    out += struct.pack("<H", len(tags))
    for tag, typ, cnt, val in tags:
        if tag == 273:
            val = data_offset
        fmt = "<HHIHH" if typ == 3 else "<HHII"
        out += struct.pack(fmt, tag, typ, cnt, val, 0) if typ == 3 else struct.pack(fmt, tag, typ, cnt, val)
    out += struct.pack("<I", 0)
    out += data
    return bytes(out)


def _raw_to_png(data: bytes, w: int, h: int, bpc: int, cs: str) -> bytes | None:
    from PyQt6.QtCore import QBuffer, QIODevice
    from PyQt6.QtGui import QImage
    if bpc != 8:
        return None
    if "Gray" in cs:
        fmt, stride = QImage.Format.Format_Grayscale8, w
    elif "CMYK" in cs:
        fmt, stride = QImage.Format.Format_CMYK8888, w * 4
    else:
        fmt, stride = QImage.Format.Format_RGB888, w * 3
    if len(data) < stride * h:
        return None
    img = QImage(data, w, h, stride, fmt).copy()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


# ------------------------------------------------------------------ Word / Excel
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read_docx(path: Path) -> str:
    """Paragraphs and table rows (cells joined by ' | ') from a .docx, pure Python."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    lines = []
    body = root.find(f"{_W}body")
    for block in body if body is not None else []:
        if block.tag == f"{_W}p":
            lines.append("".join(t.text or "" for t in block.iter(f"{_W}t")))
        elif block.tag == f"{_W}tbl":
            for row in block.iter(f"{_W}tr"):
                cells = ["".join(t.text or "" for t in c.iter(f"{_W}t")).strip() for c in row.iter(f"{_W}tc")]
                lines.append("   ".join(cells))
    return "\n".join(lines)


def read_sheet(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".csv":
        return path.read_text(encoding="utf-8-sig", errors="replace").replace(",", "   ")
    if ext == ".xls":
        converted = _libreoffice_convert(path, "xlsx")
        if not converted:
            raise ValueError("Legacy .xls needs LibreOffice installed (or save it as .xlsx).")
        path = converted
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    lines = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                lines.append("   ".join(cells))
    return "\n".join(lines)


def _libreoffice_convert(path: Path, to: str) -> Path | None:
    exe = shutil.which("soffice") or next((p for p in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe") if Path(p).exists()), None)
    if not exe:
        return None
    out = Path(tempfile.mkdtemp())
    subprocess.run([exe, "--headless", "--convert-to", to, "--outdir", str(out), str(path)],
                   capture_output=True, timeout=120)
    res = out / (path.stem + "." + to)
    return res if res.exists() else None
