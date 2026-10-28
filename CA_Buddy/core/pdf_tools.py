"""PDF toolkit operations. Every function takes input paths and returns
(output_path, info_message). All processing happens locally."""
from __future__ import annotations

import io
import os
import platform
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pymupdf

from . import pii


class ToolError(Exception):
    """An error with a message that is safe to show to the user."""


# ---------------------------------------------------------------- helpers

def human_size(n: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def open_pdf(path: str | Path, password: str = "") -> pymupdf.Document:
    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"Couldn't open {Path(path).name} as a PDF. Is the file damaged?") from exc
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            raise ToolError(
                f"{Path(path).name} is password-protected. Remove the password with "
                "Unlock first, or enter the password."
            )
    return doc


def parse_ranges(spec: str, page_count: int) -> list[list[int]]:
    """'1-3, 5, 7-' -> [[0,1,2],[4],[6..last]] (0-based)."""
    groups = []
    for part in re.split(r"[,;]", spec):
        part = part.strip().lower().replace(" ", "")
        if not part:
            continue
        m = re.fullmatch(r"(\d+|last)?(?:-(\d+|last)?)?", part)
        if not m:
            raise ToolError(f"“{part}” isn't a page range. Use a format like 1-3, 5, 8-last.")
        a, b = m.group(1), m.group(2)
        to_num = lambda s, d: page_count if s == "last" else (int(s) if s else d)  # noqa: E731
        start = to_num(a, 1)
        end = to_num(b, page_count) if "-" in part else start
        if start < 1 or end > page_count or start > end:
            raise ToolError(f"Range “{part}” is outside pages 1–{page_count}.")
        groups.append(list(range(start - 1, end)))
    if not groups:
        raise ToolError("Enter at least one page range.")
    return groups


def save_pdf(doc: pymupdf.Document, out: Path, **kw) -> None:
    doc.save(out, garbage=4, deflate=True, clean=True, **kw)


def zip_files(paths: list[Path], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.name)


_PDF_CHARS = str.maketrans({"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
                            "…": "...", "\u00a0": " "})


def pdf_text(t: str) -> str:
    """Built-in PDF fonts only cover Latin-1; replace characters they can't draw."""
    t = (t or "").translate(_PDF_CHARS).replace("₹", "Rs.")
    return "".join(c if ord(c) < 256 else "?" for c in t)


HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def color(hex_str: str, default=(0.42, 0.29, 0.72)):
    m = HEX.match(hex_str or "")
    if not m:
        return default
    v = m.group(1)
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ---------------------------------------------------------------- organise

def merge(paths: list[Path], titles: list[str], out: Path, add_index: bool,
          add_bookmarks: bool, label_first_pages: bool) -> tuple[Path, str]:
    if len(paths) < 2:
        raise ToolError("Add at least two files to merge.")
    titles = [pdf_text(t) for t in titles]
    result = pymupdf.open()
    toc, ranges = [], []
    for path, title in zip(paths, titles):
        doc = open_pdf(path)
        start = result.page_count
        result.insert_pdf(doc)
        ranges.append((title, start, result.page_count - 1))
        doc.close()

    if label_first_pages:
        for title, start, _ in ranges:
            page = result[start]
            r = page.rect
            box = pymupdf.Rect(r.x1 - 200, 18, r.x1 - 18, 40)
            page.draw_rect(box, color=(0.42, 0.29, 0.72), fill=(1, 1, 1), width=1)
            page.insert_textbox(box + (0, 5, 0, 0), title, fontsize=10, fontname="hebo",
                                color=(0.42, 0.29, 0.72), align=1)

    offset = 0
    if add_index:
        idx = result.new_page(0, width=595, height=842)
        offset = 1
        idx.insert_text((60, 80), "Index of documents", fontsize=18, fontname="hebo")
        y = 120
        idx.insert_text((60, y), "Sl.", fontsize=10, fontname="hebo")
        idx.insert_text((95, y), "Document", fontsize=10, fontname="hebo")
        idx.insert_text((470, y), "Pages", fontsize=10, fontname="hebo")
        idx.draw_line((60, y + 6), (535, y + 6), width=0.6)
        y += 26
        for i, (title, start, end) in enumerate(ranges, 1):
            if y > 790:
                break
            pages = f"{start + 2}" if start == end else f"{start + 2}–{end + 2}"
            idx.insert_text((60, y), f"{i}.", fontsize=10)
            idx.insert_textbox(pymupdf.Rect(95, y - 10, 460, y + 14), title, fontsize=10)
            idx.insert_text((470, y), pages, fontsize=10)
            y += 22

    if add_bookmarks:
        if add_index:
            toc.append([1, "Index", 1])
        for title, start, _ in ranges:
            toc.append([1, title, start + 1 + offset])
        result.set_toc(toc)

    save_pdf(result, out)
    n = result.page_count
    result.close()
    return out, f"Merged {len(paths)} files into {n} pages."


def split(path: Path, mode: str, value: str, workdir: Path, out: Path) -> tuple[Path, str]:
    doc = open_pdf(path)
    n = doc.page_count
    stem = path.stem
    if mode == "ranges":
        groups = parse_ranges(value, n)
    elif mode == "every":
        try:
            k = int(value)
            assert k >= 1
        except Exception as exc:  # noqa: BLE001
            raise ToolError("Enter how many pages each part should have, e.g. 5.") from exc
        groups = [list(range(i, min(i + k, n))) for i in range(0, n, k)]
    elif mode == "each":
        groups = [[i] for i in range(n)]
    elif mode == "size":
        try:
            limit = float(value) * 1024 * 1024
            assert limit > 0
        except Exception as exc:  # noqa: BLE001
            raise ToolError("Enter the maximum size per part in MB, e.g. 5.") from exc
        groups, current = [], []
        for i in range(n):
            trial = current + [i]
            tmp = pymupdf.open()
            tmp.insert_pdf(doc, from_page=trial[0], to_page=trial[-1])
            size = len(tmp.tobytes(garbage=3, deflate=True))
            tmp.close()
            if size > limit and current:
                groups.append(current)
                current = [i]
            else:
                current = trial
        if current:
            groups.append(current)
    else:
        raise ToolError("Choose how to split the file.")

    parts = []
    for gi, g in enumerate(groups, 1):
        part = pymupdf.open()
        for p in g:
            part.insert_pdf(doc, from_page=p, to_page=p)
        label = f"p{g[0] + 1}" if len(g) == 1 else f"p{g[0] + 1}-{g[-1] + 1}"
        p_out = workdir / f"{stem}_part{gi:02d}_{label}.pdf"
        save_pdf(part, p_out)
        part.close()
        parts.append(p_out)
    doc.close()
    if len(parts) == 1:
        shutil.copy(parts[0], out.with_suffix(".pdf"))
        return out.with_suffix(".pdf"), "Created 1 file."
    zip_files(parts, out)
    return out, f"Split into {len(parts)} files (downloaded as a zip)."


def thumbnails(path: Path, password: str = "", max_pages: int = 400) -> list[str]:
    import base64
    doc = open_pdf(path, password)
    thumbs = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        zoom = 150 / max(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom * 1.5, zoom * 1.5), alpha=False)
        thumbs.append("data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return thumbs


def organize(path: Path, pages: list[dict], out: Path) -> tuple[Path, str]:
    """pages: [{'index': 0-based original, 'rotate': 0/90/180/270}] in the new order."""
    doc = open_pdf(path)
    if not pages:
        raise ToolError("Keep at least one page.")
    result = pymupdf.open()
    for item in pages:
        i = int(item["index"])
        if not 0 <= i < doc.page_count:
            raise ToolError("Page list doesn't match the file. Reload the file and try again.")
        result.insert_pdf(doc, from_page=i, to_page=i)
        rot = int(item.get("rotate", 0)) % 360
        if rot:
            pg = result[-1]
            pg.set_rotation((pg.rotation + rot) % 360)
    orig = doc.page_count
    save_pdf(result, out)
    msg = f"Saved {result.page_count} of {orig} pages in the new order."
    result.close()
    doc.close()
    return out, msg


# ---------------------------------------------------------------- compress

LEVELS = {
    "light": dict(dpi_threshold=200, dpi_target=150, quality=80),
    "recommended": dict(dpi_threshold=150, dpi_target=110, quality=65),
    "strong": dict(dpi_threshold=100, dpi_target=80, quality=45),
    "maximum": dict(dpi_threshold=80, dpi_target=60, quality=30),
}


def _compress_once(src: Path, dst: Path, level: str, grayscale: bool) -> int:
    doc = open_pdf(src)
    try:
        doc.rewrite_images(**LEVELS[level], set_to_gray=grayscale)
    except Exception:  # noqa: BLE001  (pages without images, odd encodings)
        pass
    doc.scrub(metadata=False, xml_metadata=True, thumbnails=True, attached_files=False,
              embedded_files=False, javascript=True, reset_fields=False,
              reset_responses=False, redact_images=0, clean_pages=False, hidden_text=False,
              redactions=False, remove_links=False)
    doc.subset_fonts()
    doc.save(dst, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True,
             clean=True, use_objstms=1)
    doc.close()
    return dst.stat().st_size


def compress(path: Path, level: str, target_mb: str, grayscale: bool, out: Path) -> tuple[Path, str]:
    before = path.stat().st_size
    target = None
    if target_mb and target_mb.strip():
        try:
            target = float(target_mb) * 1024 * 1024
        except ValueError as exc:
            raise ToolError("Target size must be a number in MB, e.g. 5.") from exc
    order = list(LEVELS)
    tried = order[order.index(level):] if target else [level]
    after = before
    for lv in tried:
        after = _compress_once(path, out, lv, grayscale)
        if not target or after <= target:
            break
    if after >= before:
        shutil.copy(path, out)
        return out, f"This file is already well compressed ({human_size(before)}). No smaller version was possible."
    pct = 100 - after * 100 / before
    msg = f"Reduced from {human_size(before)} to {human_size(after)} ({pct:.0f}% smaller)."
    if target and after > target:
        msg += f" Couldn't reach {target_mb} MB; try Split by size or Grayscale."
    return out, msg


# ---------------------------------------------------------------- convert

def pdf_to_word(path: Path, out: Path) -> tuple[Path, str]:
    from pdf2docx import Converter
    open_pdf(path).close()
    cv = Converter(str(path))
    try:
        cv.convert(str(out))
    finally:
        cv.close()
    return out, "Converted to Word. Check tables and layout before sending; scanned pages need OCR first."


def pdf_to_excel(path: Path, out: Path) -> tuple[Path, str]:
    import pdfplumber
    from openpyxl import Workbook
    from openpyxl.styles import Font

    open_pdf(path).close()
    wb = Workbook()
    wb.remove(wb.active)
    count = 0
    with pdfplumber.open(str(path)) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            for tno, table in enumerate(page.extract_tables(), 1):
                if not table:
                    continue
                count += 1
                ws = wb.create_sheet(f"P{pno}_T{tno}"[:31])
                for row in table:
                    vals = []
                    for c in row:
                        c = (c or "").replace("\n", " ").strip()
                        num = re.sub(r"[,₹\s]", "", c)
                        if re.fullmatch(r"-?\d+(\.\d+)?", num) and not re.fullmatch(r"0\d+", num):
                            vals.append(float(num) if "." in num else int(num))
                        else:
                            vals.append(c)
                    ws.append(vals)
                for cell in ws[1]:
                    cell.font = Font(bold=True)
                for col in ws.columns:
                    width = max(len(str(c.value or "")) for c in col)
                    ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 60)
        if count == 0:
            ws = wb.create_sheet("Text")
            for pno, page in enumerate(pdf.pages, 1):
                for line in (page.extract_text() or "").splitlines():
                    ws.append([pno, line])
    wb.save(out)
    if count == 0:
        return out, "No tables were found, so the text was exported line by line instead."
    return out, f"Exported {count} table{'s' if count != 1 else ''} to Excel, one sheet each."


def pdf_to_images(path: Path, fmt: str, dpi: int, workdir: Path, out: Path) -> tuple[Path, str]:
    doc = open_pdf(path)
    files = []
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        p = workdir / f"{path.stem}_page{i:03d}.{fmt}"
        if fmt == "jpg":
            p.write_bytes(pix.tobytes("jpeg", jpg_quality=88))
        else:
            pix.save(p)
        files.append(p)
    doc.close()
    zip_files(files, out)
    return out, f"Saved {len(files)} page images (zip)."


def images_to_pdf(paths: list[Path], page_size: str, out: Path) -> tuple[Path, str]:
    from PIL import Image, ImageOps
    if not paths:
        raise ToolError("Add at least one image.")
    result = pymupdf.open()
    for p in paths:
        try:
            img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            raise ToolError(f"{p.name} isn't an image this tool can read.") from exc
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        w, h = img.size
        if page_size == "a4":
            pw, ph = (595, 842) if h >= w else (842, 595)
            page = result.new_page(width=pw, height=ph)
            margin = 24
            scale = min((pw - 2 * margin) / w, (ph - 2 * margin) / h)
            iw, ih = w * scale, h * scale
            rect = pymupdf.Rect((pw - iw) / 2, (ph - ih) / 2, (pw + iw) / 2, (ph + ih) / 2)
        else:
            pw, ph = w * 72 / 150, h * 72 / 150
            page = result.new_page(width=pw, height=ph)
            rect = page.rect
        page.insert_image(rect, stream=buf.getvalue())
    save_pdf(result, out)
    n = result.page_count
    result.close()
    return out, f"Created a {n}-page PDF."


def _find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        if shutil.which(name):
            return shutil.which(name)
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if os.path.exists(p):
            return p
    return None


def office_to_pdf(path: Path, workdir: Path, out: Path) -> tuple[Path, str]:
    """Word/Excel/PowerPoint to PDF via MS Office (Windows) or LibreOffice."""
    ext = path.suffix.lower()
    if platform.system() == "Windows" and ext in (".doc", ".docx"):
        try:
            from docx2pdf import convert
            convert(str(path), str(out))
            if out.exists():
                return out, "Converted with Microsoft Word."
        except Exception:  # noqa: BLE001
            pass
    soffice = _find_soffice()
    if not soffice:
        raise ToolError("Converting Office files needs Microsoft Word (Windows) or the free "
                        "LibreOffice installed on this computer.")
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(workdir), str(path)],
                   capture_output=True, timeout=180, check=False)
    produced = workdir / (path.stem + ".pdf")
    if not produced.exists():
        raise ToolError("LibreOffice couldn't convert this file.")
    shutil.move(produced, out)
    return out, "Converted to PDF."


# ---------------------------------------------------------------- OCR & text

def tesseract_available() -> bool:
    try:
        import pytesseract
        _configure_tesseract(pytesseract)
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001
        return False


def _configure_tesseract(pytesseract) -> None:
    if shutil.which("tesseract"):
        return
    for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
              "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"):
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return


def ocr_languages() -> list[str]:
    try:
        import pytesseract
        _configure_tesseract(pytesseract)
        return [l for l in pytesseract.get_languages(config="") if l != "osd"]
    except Exception:  # noqa: BLE001
        return []


def ocr_page_text(page: pymupdf.Page, lang: str = "eng") -> str:
    import pytesseract
    from PIL import Image
    _configure_tesseract(pytesseract)
    pix = page.get_pixmap(dpi=300, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang=lang)


def ocr_pdf(path: Path, lang: str, out: Path) -> tuple[Path, str]:
    if not tesseract_available():
        raise ToolError("OCR needs the free Tesseract OCR program. See the README for a "
                        "one-time install, then restart the app.")
    import pytesseract
    from PIL import Image
    _configure_tesseract(pytesseract)
    doc = open_pdf(path)
    result = pymupdf.open()
    skipped = 0
    for page in doc:
        if len(page.get_text().strip()) > 50:
            result.insert_pdf(doc, from_page=page.number, to_page=page.number)
            skipped += 1
            continue
        pix = page.get_pixmap(dpi=300, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=lang, extension="pdf")
        with pymupdf.open("pdf", pdf_bytes) as one:
            # place the OCR'd page (image + invisible text) on a page of the original size
            new = result.new_page(width=page.rect.width, height=page.rect.height)
            new.show_pdf_page(new.rect, one, 0)
    save_pdf(result, out)
    n = result.page_count
    result.close()
    doc.close()
    msg = f"Made {n - skipped} scanned page{'s' if n - skipped != 1 else ''} searchable."
    if skipped:
        msg += f" {skipped} page{'s' if skipped != 1 else ''} already had text and {'were' if skipped != 1 else 'was'} kept as is."
    return out, msg


def pdf_to_text(path: Path, out: Path) -> tuple[Path, str]:
    doc = open_pdf(path)
    parts = [f"--- Page {p.number + 1} ---\n{p.get_text()}" for p in doc]
    out.write_text("\n".join(parts), encoding="utf-8")
    doc.close()
    return out, "Extracted the text. Scanned pages come out empty unless you run OCR first."


# ---------------------------------------------------------------- security

def protect(path: Path, user_pw: str, owner_pw: str, allow_print: bool, allow_copy: bool,
            out: Path) -> tuple[Path, str]:
    if not user_pw:
        raise ToolError("Enter a password to open the file.")
    doc = open_pdf(path)
    perm = pymupdf.PDF_PERM_ACCESSIBILITY
    if allow_print:
        perm |= pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ
    if allow_copy:
        perm |= pymupdf.PDF_PERM_COPY
    doc.save(out, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=user_pw,
             owner_pw=owner_pw or user_pw + "#owner", permissions=perm, garbage=3, deflate=True)
    doc.close()
    return out, "Protected with AES-256. Share the password separately from the file."


def unlock(path: Path, password: str, out: Path) -> tuple[Path, str]:
    doc = pymupdf.open(path)
    if doc.needs_pass and not doc.authenticate(password):
        raise ToolError("That password didn't open the file. Check it and try again.")
    doc.save(out, encryption=pymupdf.PDF_ENCRYPT_NONE, garbage=3, deflate=True)
    doc.close()
    return out, "Password removed."


def redact(path: Path, terms: list[str], out: Path) -> tuple[Path, str]:
    """Permanently remove every occurrence of the given strings."""
    doc = open_pdf(path)
    hits = 0
    for page in doc:
        for term in terms:
            for line in [t for t in re.split(r"\s*\n\s*", term) if t.strip()]:
                for quad in page.search_for(line.strip(), quads=True):
                    page.add_redact_annot(quad, fill=(0, 0, 0))
                    hits += 1
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
    doc.set_metadata({})
    save_pdf(doc, out)
    doc.close()
    if hits == 0:
        return out, "None of the selected details were found as text in the PDF. Scanned pages need OCR before redaction."
    return out, f"Permanently removed {hits} occurrence{'s' if hits != 1 else ''}. The hidden text can't be recovered from this copy."


def page_sizes(path: Path) -> list[list[float]]:
    doc = open_pdf(path)
    sizes = [[round(p.rect.width, 2), round(p.rect.height, 2)] for p in doc]
    doc.close()
    return sizes


def render_page(path: Path, index: int, zoom: float = 2.0) -> bytes:
    doc = open_pdf(path)
    if not 0 <= index < doc.page_count:
        doc.close()
        raise ToolError("That page doesn't exist.")
    png = doc[index].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).tobytes("png")
    doc.close()
    return png


def find_text(path: Path, query: str, match_case: bool = False, whole_word: bool = False,
              pattern: bool = False) -> dict:
    """Return every place `query` appears: [{page, rect:[x0,y0,x1,y1], text}] in PDF points.
    pattern=True treats the query as a regular expression."""
    query = (query or "").strip()
    if not query:
        raise ToolError("Type something to find.")
    flags = 0 if match_case else re.IGNORECASE
    if pattern:
        try:
            rx = re.compile(query, flags)
        except re.error as exc:
            raise ToolError(f"That pattern isn't valid: {exc}") from exc
    doc = open_pdf(path)
    hits, text_pages = [], 0
    for pno, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            text_pages += 1
        if pattern:
            terms = sorted({m.group(0).strip() for m in rx.finditer(text) if m.group(0).strip()}, key=len, reverse=True)
        else:
            terms = [query]
        seen = set()
        for term in terms:
            for line in [x for x in re.split(r"\s*\n\s*", term) if x.strip()]:
                for r in page.search_for(line.strip()):
                    key = tuple(round(v, 1) for v in r)
                    if key in seen:
                        continue
                    found = page.get_textbox(r + (-0.5, -0.5, 0.5, 0.5)).strip() or line
                    if match_case and not pattern and line not in found:
                        continue
                    if whole_word:
                        wider = page.get_textbox(r + (-4, -0.5, 4, 0.5))
                        wb = re.compile(r"(?<![A-Za-z0-9])" + re.escape(line.strip()) + r"(?![A-Za-z0-9])", flags)
                        if not wb.search(wider):
                            continue
                    seen.add(key)
                    hits.append({"page": pno, "rect": [round(v, 2) for v in r], "text": found[:120]})
    total = doc.page_count
    doc.close()
    return {"hits": hits, "text_pages": text_pages, "pages": total}


def _style_under(page: pymupdf.Page, rect: pymupdf.Rect) -> tuple[str, float]:
    """Font family (helv / tiro / cour) and size of the text under `rect`, so a
    replacement looks like the original."""
    best = None
    for b in page.get_text("dict", clip=rect)["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                if s["text"].strip():
                    area = (pymupdf.Rect(s["bbox"]) & rect).get_area()
                    if best is None or area > best[0]:
                        best = (area, s)
    if not best:
        return "helv", max(5.0, min(rect.height * 0.75, 12.0))
    s = best[1]
    name = s["font"].lower()
    mono = s["flags"] & 8 or "cour" in name or "mono" in name
    serif = s["flags"] & 4 or "times" in name or "serif" in name and "sans" not in name
    return ("cour" if mono else "tiro" if serif else "helv"), float(s["size"])


def redact_marks(path: Path, marks: list[dict], out: Path, fill: str = "black") -> tuple[Path, str]:
    """marks: [{page, rect:[x0,y0,x1,y1], replace?: str}] in PDF points.
    Everything under each box is removed for good (text, images, drawings).
    With `replace`, the box is white and the new text is written in its place."""
    if not marks:
        raise ToolError("Mark at least one area or search result to redact.")
    colour = {"black": (0, 0, 0), "white": (1, 1, 1)}.get(fill, (0, 0, 0))
    doc = open_pdf(path)
    by_page: dict[int, list[dict]] = {}
    for m in marks:
        by_page.setdefault(int(m["page"]), []).append(m)
    replaced = boxes = 0
    writes: list = []
    for pno, ms in by_page.items():
        if not 0 <= pno < doc.page_count:
            continue
        page = doc[pno]
        for m in ms:
            r = pymupdf.Rect(m["rect"]) & page.rect
            if r.is_empty or r.width < 1 or r.height < 1:
                continue
            rep = pdf_text(str(m.get("replace") or "").strip())
            if rep:
                font, size = _style_under(page, r)
                # shrink a little to fit the box; if it still doesn't fit, let it run on to the right
                fs = size
                while fs > size * 0.5 and pymupdf.get_text_length(rep, fontname=font, fontsize=fs) > r.width:
                    fs -= 0.25
                writes.append((r, rep, font, fs))
                page.add_redact_annot(r, fill=(1, 1, 1))
                replaced += 1
            else:
                page.add_redact_annot(r, fill=colour)
                boxes += 1
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS,
                              graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
        for r, rep, font, fs in writes:
            base = r.y0 + (r.height + fs * 0.7) / 2  # vertically centred baseline
            page.insert_text((r.x0, base), rep, fontname=font, fontsize=fs, color=(0, 0, 0))
        writes.clear()
    doc.set_metadata({})
    save_pdf(doc, out)
    doc.close()
    parts = []
    if boxes:
        parts.append(f"blacked out {boxes} area{'s' if boxes != 1 else ''}" if fill == "black"
                     else f"whited out {boxes} area{'s' if boxes != 1 else ''}")
    if replaced:
        parts.append(f"replaced text in {replaced} place{'s' if replaced != 1 else ''}")
    if not parts:
        return out, "Nothing was changed: the marked areas were outside the pages."
    return out, ("Done: " + " and ".join(parts) + ". The original content under the marks is removed "
                 "from this copy and can't be recovered.")


# ---------------------------------------------------------------- finishing

POS = {
    "bottom-center": lambda r, w, m: (r.x0 + (r.width - w) / 2, r.y1 - m),
    "bottom-right": lambda r, w, m: (r.x1 - m - w, r.y1 - m),
    "bottom-left": lambda r, w, m: (r.x0 + m, r.y1 - m),
    "top-right": lambda r, w, m: (r.x1 - m - w, r.y0 + m + 8),
    "top-center": lambda r, w, m: (r.x0 + (r.width - w) / 2, r.y0 + m + 8),
    "top-left": lambda r, w, m: (r.x0 + m, r.y0 + m + 8),
}


def _page_selection(spec: str, n: int) -> set[int]:
    spec = (spec or "").strip().lower()
    if spec in ("", "all"):
        return set(range(n))
    if spec == "first":
        return {0}
    if spec == "last":
        return {n - 1}
    return {p for g in parse_ranges(spec, n) for p in g}


def page_numbers(path: Path, fmt: str, position: str, start: int, fontsize: float,
                 skip_first: bool, out: Path) -> tuple[Path, str]:
    doc = open_pdf(path)
    total = doc.page_count - (1 if skip_first else 0)
    fmt = pdf_text(fmt or "Page {n} of {total}")
    count = 0
    for page in doc:
        if skip_first and page.number == 0:
            continue
        num = page.number - (1 if skip_first else 0) + start
        text = fmt.replace("{n}", str(num)).replace("{total}", str(total + start - 1))
        w = pymupdf.get_text_length(text, fontname="helv", fontsize=fontsize)
        page.wrap_contents()
        rect = page.rect
        x, y = POS.get(position, POS["bottom-center"])(rect, w, 24)
        # page.rect is in unrotated space only for rotation 0; derotate the point
        pt = pymupdf.Point(x, y) * page.derotation_matrix
        page.insert_text(pt, text, fontsize=fontsize, fontname="helv", color=(0.15, 0.15, 0.2),
                         rotate=page.rotation)
        count += 1
    save_pdf(doc, out)
    doc.close()
    return out, f"Numbered {count} pages."


def watermark(path: Path, text: str, opacity: float, colour: str, fontsize: float,
              diagonal: bool, pages: str, out: Path) -> tuple[Path, str]:
    text = pdf_text(text)
    if not text.strip():
        raise ToolError("Enter the watermark text.")
    doc = open_pdf(path)
    targets = _page_selection(pages, doc.page_count)
    rgb = color(colour, (0.6, 0.6, 0.65))
    for page in doc:
        if page.number not in targets:
            continue
        page.wrap_contents()
        r = page.rect
        w = pymupdf.get_text_length(text, fontname="hebo", fontsize=fontsize)
        centre = pymupdf.Point(r.width / 2, r.height / 2)
        start = pymupdf.Point(centre.x - w / 2, centre.y + fontsize / 3)
        # angle measured on screen; adjust for pages stored with a /Rotate value
        angle = (45 if diagonal else 0) + page.rotation
        page.insert_text(start * page.derotation_matrix, text, fontsize=fontsize, fontname="hebo",
                         color=rgb, fill_opacity=opacity, stroke_opacity=opacity,
                         morph=(centre * page.derotation_matrix, pymupdf.Matrix(-angle) if page.rotation else pymupdf.Matrix(angle)))
    save_pdf(doc, out)
    doc.close()
    return out, f"Added the watermark to {len(targets)} page{'s' if len(targets) != 1 else ''}."


def stamp(path: Path, text: str, image: Path | None, position: str, pages: str,
          width_pt: float, colour: str, out: Path) -> tuple[Path, str]:
    """Text stamp (e.g. 'Certified true copy') and/or an image (signature, seal)."""
    text = pdf_text(text)
    if not text.strip() and image is None:
        raise ToolError("Enter stamp text or add a signature/seal image.")
    doc = open_pdf(path)
    targets = _page_selection(pages, doc.page_count)
    rgb = color(colour, (0.42, 0.29, 0.72))
    img_bytes, ratio = None, 1.0
    if image is not None:
        from PIL import Image
        try:
            im = Image.open(image)
        except Exception as exc:  # noqa: BLE001
            raise ToolError("The stamp image couldn't be read. Use PNG or JPG.") from exc
        ratio = im.height / im.width
        img_bytes = image.read_bytes()
    for page in doc:
        if page.number not in targets:
            continue
        page.wrap_contents()
        r = page.rect
        text_h = 0
        lines = [l for l in text.splitlines() if l.strip()]
        if lines:
            text_h = 14 * len(lines) + 10
        img_h = width_pt * ratio if img_bytes else 0
        total_h = text_h + img_h
        m = 30
        x = {"left": r.x0 + m, "center": r.x0 + (r.width - width_pt) / 2,
             "right": r.x1 - m - width_pt}[position.split("-")[1]]
        y = r.y0 + m if position.startswith("top") else r.y1 - m - total_h
        box = pymupdf.Rect(x, y, x + width_pt, y + total_h) * page.derotation_matrix
        box.normalize()
        if img_bytes:
            img_rect = pymupdf.Rect(x, y, x + width_pt, y + img_h) * page.derotation_matrix
            img_rect.normalize()
            page.insert_image(img_rect, stream=img_bytes, keep_proportion=True,
                              rotate=-page.rotation % 360 if page.rotation else 0)
        if lines:
            tb = pymupdf.Rect(x, y + img_h, x + width_pt, y + total_h)
            shape = page.new_shape()
            shape.draw_rect(tb * page.derotation_matrix)
            shape.finish(color=rgb, width=1.4)
            shape.commit()
            page.insert_textbox(pymupdf.Rect(tb.x0 + 4, tb.y0 + 5, tb.x1 - 4, tb.y1) * page.derotation_matrix,
                                "\n".join(lines), fontsize=10.5, fontname="hebo", color=rgb, align=1,
                                rotate=page.rotation)
    save_pdf(doc, out)
    doc.close()
    return out, f"Stamped {len(targets)} page{'s' if len(targets) != 1 else ''}."


def info(path: Path) -> dict:
    doc = pymupdf.open(path)
    d = {"pages": doc.page_count if not doc.needs_pass else None, "encrypted": doc.needs_pass,
         "size": human_size(path.stat().st_size)}
    doc.close()
    return d


def detect_redaction_terms(path: Path) -> list[dict]:
    from .notice import extract_text
    text, _ = extract_text(path, allow_ocr=False)
    return pii.detect(text)
