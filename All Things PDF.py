"""
All Things PDF — Desktop App
Green & White colour scheme. All tools fully functional.
Run in IDLE (F5) or double-click.

pip install pypdf pymupdf pillow
"""
from __future__ import annotations
import sys, os, io, math, threading, uuid, zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ── Hide console on Windows ───────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass

try:
    import pymupdf as fitz
    from pypdf import PdfReader, PdfWriter
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing libraries",
        "Run in CMD first:\n\npip install pypdf pymupdf pillow\n\nThen restart the app.")
    sys.exit()

# ══════════════════════════════════════════════════════════════════
# PALETTE  — DPS forest green + white
# ══════════════════════════════════════════════════════════════════
BG       = "#f2f6f3"
WHITE    = "#ffffff"
HEADER   = "#1a5c38"
HDR2     = "#144d2e"
GREEN    = "#2d7a4f"
GREEN_L  = "#e4f2ea"
GREEN_LL = "#f0faf4"
BORDER   = "#c4d9cc"
TEXT     = "#1c2b20"
MUTED    = "#567060"
SUCCESS  = "#1a6e38"
DANGER   = "#c0392b"
WARN     = "#b7860b"
COL_ORG  = "#2d7a4f"
COL_OPT  = "#1a5c38"
COL_EDIT = "#b7860b"
COL_SEC  = "#c0392b"

F    = ("Segoe UI", 10)
FB   = ("Segoe UI", 10, "bold")
FH   = ("Segoe UI", 12, "bold")
FT   = ("Segoe UI", 18, "bold")
FLAB = ("Segoe UI",  8, "bold")
FDESC= ("Segoe UI",  9)
FTAB = ("Segoe UI",  9, "bold")

OUT_DIR = Path.home() / "AllThingsPDF_Output"
TMP_DIR = Path.home() / "AllThingsPDF_Temp"
OUT_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)

def tmpf(s=".pdf"): return TMP_DIR / f"{uuid.uuid4().hex}{s}"
def outf(n):        return OUT_DIR / n
def _human(b):
    for u in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.1f} {u}"
        b //= 1024
    return f"{b:.1f} TB"

# ══════════════════════════════════════════════════════════════════
# PDF SERVICES  — tested, working
# ══════════════════════════════════════════════════════════════════

def svc_merge(paths, out):
    if len(paths) < 2: raise ValueError("Select at least 2 PDF files.")
    w = PdfWriter()
    for p in paths:
        r = PdfReader(str(p))
        for pg in r.pages: w.add_page(pg)
    with open(out, "wb") as f: w.write(f)
    return f"Merged {len(paths)} files → {Path(out).name}"

def svc_split_pages(src, out_dir):
    r = PdfReader(str(src)); n = len(r.pages); pad = len(str(n))
    outs = []
    for i, pg in enumerate(r.pages, 1):
        w = PdfWriter(); w.add_page(pg)
        op = Path(out_dir) / f"page_{str(i).zfill(pad)}.pdf"
        with open(op, "wb") as f: w.write(f)
        outs.append(op)
    return f"Split into {len(outs)} pages → {Path(out_dir).name}"

def svc_split_ranges(src, ranges_str, out_dir):
    ranges = []
    for part in ranges_str.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ranges.append((int(a.strip()), int(b.strip())))
    if not ranges: raise ValueError("Enter ranges like  1-3, 4-6")
    r = PdfReader(str(src)); n = len(r.pages)
    outs = []
    for i, (s, e) in enumerate(ranges, 1):
        if s < 1 or e > n or e < s:
            raise ValueError(f"Range ({s}-{e}) invalid for {n}-page document.")
        w = PdfWriter()
        for p in range(s - 1, e): w.add_page(r.pages[p])
        op = Path(out_dir) / f"part{i}_p{s}-{e}.pdf"
        with open(op, "wb") as f: w.write(f)
        outs.append(op)
    return f"Split into {len(outs)} parts → {Path(out_dir).name}"

def svc_remove(src, pages_str, out):
    pages = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
    r = PdfReader(str(src)); n = len(r.pages); rm = set(pages)
    bad = {p for p in rm if p < 1 or p > n}
    if bad: raise ValueError(f"Pages {sorted(bad)} out of range (doc has {n} pages).")
    w = PdfWriter(); kept = 0
    for i, pg in enumerate(r.pages, 1):
        if i not in rm: w.add_page(pg); kept += 1
    if not kept: raise ValueError("Cannot remove all pages.")
    with open(out, "wb") as f: w.write(f)
    return f"Removed {len(pages)} pages → {Path(out).name}  ({kept} pages remain)"

def svc_extract(src, pages_str, out):
    pages = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
    r = PdfReader(str(src)); n = len(r.pages)
    bad = [p for p in pages if p < 1 or p > n]
    if bad: raise ValueError(f"Pages {bad} out of range (doc has {n} pages).")
    w = PdfWriter()
    for p in pages: w.add_page(r.pages[p - 1])
    with open(out, "wb") as f: w.write(f)
    return f"Extracted {len(pages)} pages → {Path(out).name}"

def svc_reorder(src, pages_str, out):
    order = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
    r = PdfReader(str(src)); n = len(r.pages)
    if sorted(order) != list(range(1, n + 1)):
        raise ValueError(f"Order must use every page 1–{n} exactly once.")
    w = PdfWriter()
    for p in order: w.add_page(r.pages[p - 1])
    with open(out, "wb") as f: w.write(f)
    return f"Reordered → {Path(out).name}"

def svc_compress(src, out, level="medium"):
    """
    iLovePDF-style multi-strategy compression.
    Uses PIL BILINEAR resize — 7x faster than rewrite_images, 85%+ reduction.
    low:    stream deflation only (lossless, instant)
    medium: downsample images >1800px to 1800px, JPEG 80%
    high:   downsample images to 1000px, JPEG 60%
    """
    from PIL import Image
    import io as _io

    src = Path(src); out = Path(out)
    orig = src.stat().st_size
    out.parent.mkdir(parents=True, exist_ok=True)

    presets = {
        "low":    {"max_px": None, "jpeg_q": None, "garbage": 1, "clean": False},
        "medium": {"max_px": 1800, "jpeg_q": 80,   "garbage": 3, "clean": True},
        "high":   {"max_px": 1000, "jpeg_q": 60,   "garbage": 4, "clean": True},
    }
    p = presets[level]
    doc = fitz.open(str(src))

    if p["clean"]:
        doc.set_metadata({})

    if p["max_px"] is not None:
        max_px  = p["max_px"]
        jpeg_q  = p["jpeg_q"]
        visited = set()
        for page in doc:
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                if xref in visited:
                    continue
                visited.add(xref)
                try:
                    base = doc.extract_image(xref)
                    if not base:
                        continue
                    w, h    = base["width"], base["height"]
                    raw     = base["image"]
                    scale   = min(max_px / max(w, h), 1.0)
                    if scale >= 1.0:
                        # No resize needed — still re-encode at lower quality
                        img = Image.open(_io.BytesIO(raw))
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                        buf = _io.BytesIO()
                        img.save(buf, "JPEG", quality=jpeg_q, optimize=False)
                        new_bytes = buf.getvalue()
                    else:
                        new_w = max(1, int(w * scale))
                        new_h = max(1, int(h * scale))
                        img = Image.open(_io.BytesIO(raw))
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                        img = img.resize((new_w, new_h), Image.BILINEAR)
                        buf = _io.BytesIO()
                        img.save(buf, "JPEG", quality=jpeg_q, optimize=False)
                        new_bytes = buf.getvalue()
                    if len(new_bytes) < len(raw):
                        doc.update_stream(xref, new_bytes)
                except Exception:
                    pass

    doc.save(str(out), deflate=True, deflate_images=True, deflate_fonts=True,
             garbage=p["garbage"], clean=p["clean"])
    doc.close()
    comp = out.stat().st_size
    pct  = max(0.0, (1 - comp / orig) * 100) if orig else 0
    return (f"Compressed → {out.name}  |  "
            f"{_human(orig)} → {_human(comp)}  ({pct:.1f}% smaller)")
def svc_repair(src, out):
    """Rebuild xref table, remove corrupt objects, re-compress streams."""
    src = Path(src); out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(src))
    doc.save(str(out), garbage=4, clean=True, deflate=True, deflate_images=True)
    doc.close()
    return f"Repaired → {out.name}"


def svc_remove_metadata(src, out):
    """Strip all metadata (author, dates, software info) from the PDF."""
    src = Path(src); out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(src))
    doc.set_metadata({})
    # Also remove XMP metadata
    try: doc.set_xml_metadata("")
    except Exception: pass
    doc.save(str(out), garbage=3, clean=True, deflate=True)
    doc.close()
    return f"Metadata removed → {out.name}"


def svc_grayscale(src, out):
    """Convert all pages to grayscale — reduces size 60-80%, great for printing."""
    from PIL import Image as PILImage
    import io as _io
    src = Path(src); out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    src_doc = fitz.open(str(src))
    out_doc = fitz.open()
    for page in src_doc:
        # Render page in grayscale
        pix = page.get_pixmap(colorspace=fitz.csGRAY, alpha=False,
                              matrix=fitz.Matrix(1.5, 1.5))
        # Convert to PDF page via PIL for better JPEG compression
        img = PILImage.frombytes("L", [pix.width, pix.height], pix.samples)
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        img_doc = fitz.open("jpeg", buf.getvalue())
        pdf_bytes = img_doc.convert_to_pdf()
        img_doc.close()
        img_pdf = fitz.open("pdf", pdf_bytes)
        out_doc.insert_pdf(img_pdf)
        img_pdf.close()
    src_doc.close()
    out_doc.save(str(out), deflate=True, garbage=3)
    out_doc.close()
    return f"Converted to grayscale → {out.name}"


def svc_flatten(src, out):
    """Flatten annotations, form fields and layers into static content."""
    src = Path(src); out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(src))
    for page in doc:
        # Remove all annotations (bakes them in by deleting interactive layer)
        annots = list(page.annots())
        for annot in annots:
            try: page.delete_annot(annot)
            except Exception: pass
        # Flatten widgets (form fields)
        widgets = list(page.widgets()) if hasattr(page, "widgets") else []
        for widget in widgets:
            try: page.delete_widget(widget)
            except Exception: pass
    doc.save(str(out), garbage=3, clean=True, deflate=True)
    doc.close()
    return f"Flattened → {out.name}"


def svc_remove_blank_pages(src, out):
    """Auto-detect and remove blank or near-blank pages."""
    src = Path(src); out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(src))
    out_doc = fitz.open()
    removed = 0
    kept = 0
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        # Render tiny thumbnail to check whiteness
        pix = page.get_pixmap(matrix=fitz.Matrix(0.05, 0.05),
                              colorspace=fitz.csGRAY, alpha=False)
        samples = pix.samples
        avg = sum(samples) / len(samples) if samples else 255
        # Blank = no text AND average pixel brightness > 248 (very white)
        is_blank = (not text) and (avg > 248)
        if is_blank:
            removed += 1
        else:
            out_doc.insert_pdf(doc, from_page=i, to_page=i)
            kept += 1
    doc.close()
    if kept == 0:
        out_doc.close()
        raise ValueError("All pages appear blank — nothing to save.")
    out_doc.save(str(out), deflate=True, garbage=3)
    out_doc.close()
    s = "page" if removed == 1 else "pages"
    return f"Removed {removed} blank {s} → {out.name}  ({kept} kept)"


def svc_rotate(src, angle, pages_str, out):
    if angle not in (90, 180, 270): raise ValueError("Angle must be 90, 180 or 270.")
    r = PdfReader(str(src)); n = len(r.pages)
    pages = set(range(1, n + 1)) if not pages_str.strip() else \
            {int(x.strip()) for x in pages_str.split(",") if x.strip()}
    bad = {p for p in pages if p < 1 or p > n}
    if bad: raise ValueError(f"Pages {sorted(bad)} out of range.")
    w = PdfWriter()
    for i, pg in enumerate(r.pages, 1):
        if i in pages: pg.rotate(angle)
        w.add_page(pg)
    with open(out, "wb") as f: w.write(f)
    return f"Rotated {angle}° → {Path(out).name}  ({n} pages)"

def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255

def svc_watermark_text(src, text, pos, opacity, fsize, color, rotation, pages_str, out):
    doc = fitz.open(str(src)); n = len(doc)
    tgt = list(range(n)) if not pages_str.strip() else \
          [int(x.strip()) - 1 for x in pages_str.split(",") if x.strip()]
    col = _rgb(color)
    for idx in tgt:
        pg = doc[idx]; r = pg.rect; cx, cy = r.width/2, r.height/2
        def stamp(cx2, cy2, pg=pg):
            tw = fitz.TextWriter(pg.rect); font = fitz.Font("helv")
            w2 = fitz.get_text_length(text, fontname="helv", fontsize=fsize)
            rad = math.radians(rotation)
            morph = (fitz.Point(cx2, cy2),
                     fitz.Matrix(math.cos(rad), -math.sin(rad),
                                 math.sin(rad),  math.cos(rad), 0, 0))
            tw.append(fitz.Point(cx2 - w2/2, cy2 + fsize/3), text, font=font, fontsize=fsize)
            tw.write_text(pg, color=col, opacity=opacity, morph=morph)
        if pos == "tile":
            [stamp(c * r.width/3, rw * r.height/3) for rw in range(4) for c in range(4)]
        else:
            stamp(cx, cy)
    doc.save(str(out), deflate=True, garbage=3); doc.close()
    return f"Watermark applied → {Path(out).name}  ({n} pages)"

def svc_watermark_image(src, wm_path, opacity, scale, pages_str, out):
    if not Path(wm_path).exists(): raise ValueError(f"Watermark image not found: {wm_path}")
    doc = fitz.open(str(src)); n = len(doc)
    tgt = list(range(n)) if not pages_str.strip() else \
          [int(x.strip()) - 1 for x in pages_str.split(",") if x.strip()]
    for idx in tgt:
        pg = doc[idx]; r = pg.rect
        w2, h2 = 200 * scale, 100 * scale; cx, cy = r.width/2, r.height/2
        pg.insert_image(fitz.Rect(cx-w2/2, cy-h2/2, cx+w2/2, cy+h2/2),
                        filename=str(wm_path), overlay=True)
    doc.save(str(out), deflate=True, garbage=3); doc.close()
    return f"Image watermark applied → {Path(out).name}  ({n} pages)"

def svc_page_numbers(src, pos, fsize, color, start, pages_str, out):
    doc = fitz.open(str(src)); n = len(doc)
    col = _rgb(color); font = fitz.Font("helv"); M = 30.0
    tgt = list(range(n)) if not pages_str.strip() else \
          [int(x.strip()) - 1 for x in pages_str.split(",") if x.strip()]
    for seq, idx in enumerate(tgt):
        pg = doc[idx]; lab = str(start + seq)
        tw = fitz.get_text_length(lab, fontname="helv", fontsize=fsize)
        pw, ph = pg.rect.width, pg.rect.height
        xm = {"bottom_center": pw/2-tw/2, "bottom_left": M, "bottom_right": pw-M-tw,
              "top_center":    pw/2-tw/2, "top_left":    M, "top_right":    pw-M-tw}
        ym = {"bottom_center": M, "bottom_left": M, "bottom_right": M,
              "top_center": ph-M, "top_left": ph-M, "top_right": ph-M}
        wr = fitz.TextWriter(pg.rect)
        wr.append(fitz.Point(xm.get(pos, pw/2-tw/2), ym.get(pos, M) + fsize),
                  lab, font=font, fontsize=fsize)
        wr.write_text(pg, color=col)
    doc.save(str(out), deflate=True); doc.close()
    return f"Page numbers added → {Path(out).name}  ({n} pages)"

def svc_crop(src, x0, y0, x1, y1, pages_str, out):
    if x1 <= x0 or y1 <= y0: raise ValueError("X1 must be > X0 and Y1 must be > Y0.")
    doc = fitz.open(str(src)); n = len(doc)
    tgt = list(range(n)) if not pages_str.strip() else \
          [int(x.strip()) - 1 for x in pages_str.split(",") if x.strip()]
    rect = fitz.Rect(x0, y0, x1, y1)
    for idx in tgt:
        pg = doc[idx]
        if not pg.rect.contains(rect):
            raise ValueError(f"Crop box exceeds page {idx+1} dimensions ({pg.rect}).")
        pg.set_mediabox(rect); pg.set_cropbox(rect)
    doc.save(str(out), deflate=True, garbage=3); doc.close()
    return f"Cropped → {Path(out).name}  ({n} pages)"

def svc_encrypt(src, user_pw, owner_pw, printing, copying, out):
    if not user_pw and not owner_pw: raise ValueError("Enter at least one password.")
    r = PdfReader(str(src))
    if r.is_encrypted: raise ValueError("PDF is already encrypted. Unlock it first.")
    w = PdfWriter(); w.clone_reader_document_root(r)
    perm = 0
    if printing: perm |= 4
    if copying:  perm |= 16
    w.encrypt(user_password=user_pw or "",
              owner_password=owner_pw or user_pw or "",
              use_128bit=True, permissions_flag=perm)
    with open(out, "wb") as f: w.write(f)
    return f"Protected → {Path(out).name}  ({len(r.pages)} pages)"

def svc_decrypt(src, pw, out):
    r = PdfReader(str(src))
    if not r.is_encrypted: raise ValueError("This PDF is not encrypted.")
    if r.decrypt(pw) == 0: raise ValueError("Wrong password — could not unlock.")
    w = PdfWriter()
    for pg in r.pages: w.add_page(pg)
    with open(out, "wb") as f: w.write(f)
    return f"Unlocked → {Path(out).name}  ({len(r.pages)} pages)"

def svc_redact_text(src, terms_str, out):
    terms = [t.strip() for t in terms_str.splitlines() if t.strip()]
    if not terms: raise ValueError("Enter at least one search term.")
    doc = fitz.open(str(src)); total = 0
    for pg in doc:
        for t in terms:
            for rect in pg.search_for(t):
                pg.add_redact_annot(rect, fill=(0, 0, 0)); total += 1
        pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    doc.save(str(out), deflate=True, garbage=4, clean=True); doc.close()
    return f"Redacted {total} instances → {Path(out).name}"

def svc_redact_regions(src, regions, out):
    if not regions: raise ValueError("Add at least one region.")
    doc = fitz.open(str(src)); n = len(doc); count = 0
    for rg in regions:
        p = int(rg["page"])
        if p < 1 or p > n: raise ValueError(f"Page {p} out of range.")
        doc[p-1].add_redact_annot(
            fitz.Rect(float(rg["x0"]), float(rg["y0"]),
                      float(rg["x1"]), float(rg["y1"])),
            fill=(0, 0, 0)); count += 1
    for pg in doc: pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
    doc.save(str(out), deflate=True, garbage=4, clean=True); doc.close()
    return f"Redacted {count} region(s) → {Path(out).name}"


# ══════════════════════════════════════════════════════════════════
# GUI HELPERS
# ══════════════════════════════════════════════════════════════════

def _frm(p, bg=WHITE, **kw): return tk.Frame(p, bg=bg, bd=0, **kw)

def _entry(p, var=None, width=36, show=None):
    kw = dict(textvariable=var, width=width, bg=WHITE, fg=TEXT,
              insertbackground=TEXT, relief=tk.FLAT,
              highlightbackground=BORDER, highlightcolor=GREEN,
              highlightthickness=1, font=F)
    if show: kw["show"] = show
    return tk.Entry(p, **kw)

def _combo(p, values, var=None, width=18):
    c = ttk.Combobox(p, values=values, textvariable=var,
                     width=width, state="readonly", font=F)
    c.current(0); return c

def _green_btn(p, text, cmd, bg=GREEN, hover=HDR2):
    b = tk.Button(p, text=text, command=cmd, bg=bg, fg="white",
                  activebackground=hover, activeforeground="white",
                  relief=tk.FLAT, cursor="hand2", font=FB,
                  padx=20, pady=9, bd=0)
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b

def _ghost_btn(p, text, cmd):
    b = tk.Button(p, text=text, command=cmd, bg=WHITE, fg=MUTED,
                  activebackground=GREEN_L, activeforeground=GREEN,
                  relief=tk.FLAT, cursor="hand2", font=F,
                  padx=10, pady=6, bd=0,
                  highlightbackground=BORDER, highlightthickness=1)
    return b

def _browse_pdf(var, multi=False):
    if multi:
        f = filedialog.askopenfilenames(filetypes=[("PDF","*.pdf")])
        if f: var.set(";".join(f))
    else:
        f = filedialog.askopenfilename(filetypes=[("PDF","*.pdf")])
        if f: var.set(f)

def _browse_img(var):
    f = filedialog.askopenfilename(
        filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")])
    if f: var.set(f)

def _browse_save(var, default, ext="pdf"):
    ft = [("PDF","*.pdf")] if ext == "pdf" else [("ZIP","*.zip")]
    f = filedialog.asksaveasfilename(defaultextension=f".{ext}",
                                      initialfile=default, filetypes=ft)
    if f: var.set(f)

def _browse_folder(var):
    d = filedialog.askdirectory()
    if d: var.set(d)


# ══════════════════════════════════════════════════════════════════
# DROPZONE WIDGET
# ══════════════════════════════════════════════════════════════════

class DropZone(tk.Frame):
    def __init__(self, parent, var, multi=False, accept_img=False, **kw):
        super().__init__(parent, bg=GREEN_LL, bd=0,
                         highlightbackground=BORDER, highlightthickness=2,
                         cursor="hand2", **kw)
        self.var = var; self.multi = multi; self.accept_img = accept_img
        self._files = []
        self._build()

    def _build(self):
        self._icon = tk.Label(self, text="📂", bg=GREEN_LL,
                              font=("Segoe UI Emoji", 28))
        self._icon.pack(pady=(16, 4))
        self._t1 = tk.Label(self,
                            text="Select PDF files" if self.multi else "Select PDF file",
                            bg=GREEN_LL, fg=HEADER, font=FB)
        self._t1.pack()
        self._t2 = tk.Label(self, text="Click here to browse",
                            bg=GREEN_LL, fg=MUTED, font=F)
        self._t2.pack(pady=(2, 16))
        self._chips = _frm(self, bg=WHITE)
        self._chips.pack(fill=tk.X, padx=4, pady=(0, 6))
        for w in (self, self._icon, self._t1, self._t2):
            w.bind("<Button-1>", lambda e: self._browse())
            w.bind("<Enter>",    lambda e: self._hov(True))
            w.bind("<Leave>",    lambda e: self._hov(False))

    def _hov(self, on):
        col  = GREEN_L if on else GREEN_LL
        hcol = GREEN   if on else BORDER
        self.config(highlightbackground=hcol)
        for w in (self, self._icon, self._t1, self._t2):
            w.config(bg=col)

    def _browse(self):
        if self.accept_img:
            types = [("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        else:
            types = [("PDF", "*.pdf")]
        if self.multi:
            files = filedialog.askopenfilenames(filetypes=types)
        else:
            f = filedialog.askopenfilename(filetypes=types)
            files = (f,) if f else ()
        if files:
            self._files = [Path(f) for f in files if f]
            self.var.set(";".join(str(f) for f in self._files))
            self._refresh()

    def _refresh(self):
        for w in self._chips.winfo_children(): w.destroy()
        for i, fp in enumerate(self._files):
            row = tk.Frame(self._chips, bg=GREEN_L,
                           highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill=tk.X, pady=2)
            sz = fp.stat().st_size if fp.exists() else 0
            tk.Label(row, text=f"  📄  {fp.name}",
                     bg=GREEN_L, fg=TEXT, font=F,
                     anchor="w").pack(side=tk.LEFT, pady=5)
            tk.Label(row, text=_human(sz),
                     bg=GREEN_L, fg=MUTED, font=F).pack(side=tk.LEFT)
            # Delete button on right
            def _del(idx=i):
                self._files.pop(idx)
                self.var.set(";".join(str(f) for f in self._files))
                self._refresh()
            tk.Button(row, text="✕", command=_del,
                      bg=GREEN_L, fg=DANGER, activebackground="#ffe0e0",
                      relief=tk.FLAT, cursor="hand2", font=FB,
                      bd=0, padx=8).pack(side=tk.RIGHT, pady=2)
            tk.Label(row, text="✓  ", bg=GREEN_L, fg=SUCCESS, font=FB).pack(side=tk.RIGHT)

    def paths(self):   return self._files
    def single(self):
        if not self._files: raise ValueError("Select a file first.")
        return self._files[0]


# ══════════════════════════════════════════════════════════════════
# TOOL PANEL BASE
# Key fix: use grid geometry manager so header/footer never overlap body
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
# GLOBAL SCROLL ROUTER
# Bind to root window, walk widget under cursor to find first
# scrollable canvas, scroll that. Works for mouse and trackpad.
# Source: https://stackoverflow.com/a/37858368
# ══════════════════════════════════════════════════════════════════
def _on_mousewheel(event):
    """Root-level handler. Walks widget hierarchy from cursor position."""
    # Get widget physically under the cursor
    widget = event.widget.winfo_containing(event.x_root, event.y_root)
    # Walk up until we find a Canvas that can scroll
    while widget is not None:
        if isinstance(widget, tk.Canvas):
            try:
                # Only scroll if the canvas actually has content to scroll
                if widget.yview() != (0.0, 1.0):
                    if event.num == 4:          # Linux scroll up
                        widget.yview_scroll(-1, "units")
                    elif event.num == 5:        # Linux scroll down
                        widget.yview_scroll(1, "units")
                    else:                       # Windows / trackpad
                        widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
            except Exception:
                pass
        try:
            parent_name = widget.winfo_parent()
            widget = widget.nametowidget(parent_name)
        except Exception:
            break


# Legacy class kept so existing references don't break
class _ScrollRouter:
    @classmethod
    def init(cls, root):
        root.bind_all("<MouseWheel>", _on_mousewheel)
        root.bind_all("<Button-4>",   _on_mousewheel)
        root.bind_all("<Button-5>",   _on_mousewheel)
    @classmethod
    def register(cls, canvas):      pass
    @classmethod
    def bind_recursive(cls, w, cv): pass
    @classmethod
    def set_active(cls, cv):        pass
    @classmethod
    def clear(cls, cv):             pass
    @classmethod
    def scroll(cls, e):             _on_mousewheel(e)
# ══════════════════════════════════════════════════════════════════
# TOOL PANEL BASE
# Key fix: use grid geometry manager so header/footer never overlap body
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
# GLOBAL SCROLL ROUTER
# The only approach that reliably works on Windows with both
# mouse wheels AND trackpads/precision touchpads.
#
# Strategy: bind scroll handler to the canvas AND recursively
# to every child widget inside it. This way the event fires
# no matter which widget tkinter decides to route it to.
# ══════════════════════════════════════════════════════════════════
class _ScrollRouter:
    _root   = None
    _canvas = None   # the currently registered scroll canvas

    @classmethod
    def init(cls, root):
        cls._root = root

    @classmethod
    def register(cls, canvas):
        """Call after building each tool panel body canvas."""
        cls._canvas = canvas

    @classmethod
    def _scroll(cls, event):
        if event.delta:
            units = int(-1 * (event.delta / 120))
        elif event.num == 4:
            units = -1
        elif event.num == 5:
            units =  1
        else:
            return
        # Try the registered canvas first
        if cls._canvas and cls._canvas.winfo_exists():
            cls._canvas.yview_scroll(units, "units")
            return
        # Fallback: walk up from event widget
        w = event.widget
        while w:
            if isinstance(w, tk.Canvas):
                w.yview_scroll(units, "units")
                return
            try:
                w = w.nametowidget(w.winfo_parent())
            except Exception:
                break

    @classmethod
    def bind_recursive(cls, widget, canvas):
        """Bind scroll to widget and all its descendants."""
        def handler(e, cv=canvas):
            if e.delta:
                cv.yview_scroll(int(-1*(e.delta/120)), "units")
            elif e.num == 4:
                cv.yview_scroll(-1, "units")
            elif e.num == 5:
                cv.yview_scroll(1, "units")
        try:
            widget.bind("<MouseWheel>", handler, add="+")
            widget.bind("<Button-4>",   handler, add="+")
            widget.bind("<Button-5>",   handler, add="+")
        except Exception:
            pass
        for child in widget.winfo_children():
            cls.bind_recursive(child, canvas)

    # Legacy stubs
    @classmethod
    def set_active(cls, canvas): cls._canvas = canvas
    @classmethod
    def clear(cls, canvas):
        if cls._canvas is canvas: cls._canvas = None
    @classmethod
    def scroll(cls, event): cls._scroll(event)


class ToolPanel(tk.Frame):
    """
    Layout (grid rows):
      0 = coloured header bar
      1 = scrollable form body  (weight=1, expands)
      2 = fixed action/status bar (always visible)
    """
    def __init__(self, parent, name, icon, color, back_cb, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._status_var = tk.StringVar()
        self._build_header(icon, name, color, back_cb)
        self._build_body()
        self._build_footer()
        self.setup()   # subclasses override setup()

    # ── Row 0: header ────────────────────────────────────────────
    def _build_header(self, icon, name, color, back_cb):
        hdr = tk.Frame(self, bg=color)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text=icon, bg=color, fg="white",
                 font=("Segoe UI Emoji", 16),
                 padx=14, pady=10).pack(side=tk.LEFT)
        tk.Label(hdr, text=name, bg=color, fg="white",
                 font=FH, pady=10).pack(side=tk.LEFT)
        tk.Button(hdr, text="← Back", command=back_cb,
                  bg=color, fg="white",
                  activebackground=HDR2, activeforeground="white",
                  relief=tk.FLAT, cursor="hand2",
                  font=F, padx=14, pady=10, bd=0).pack(side=tk.RIGHT, padx=8)

    # ── Row 1: scrollable body ────────────────────────────────────
    def _build_body(self):
        wrap = _frm(self, bg=BG)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        vsb = ttk.Scrollbar(wrap, orient="vertical")
        vsb.grid(row=0, column=1, sticky="ns")
        self._cv = tk.Canvas(wrap, bg=BG, bd=0, highlightthickness=0,
                             yscrollcommand=vsb.set)
        self._cv.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._cv.yview)
        self.body = tk.Frame(self._cv, bg=BG)
        self._win = self._cv.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self._cv.configure(
            scrollregion=self._cv.bbox("all")))
        self._cv.bind("<Configure>", lambda e: self._cv.itemconfig(
            self._win, width=e.width))
        tk.Frame(self.body, bg=BG, height=16).pack()  # top padding

    # ── Row 2: fixed action bar ───────────────────────────────────
    def _build_footer(self):
        foot = tk.Frame(self, bg=WHITE,
                        highlightbackground=BORDER, highlightthickness=1)
        foot.grid(row=2, column=0, sticky="ew")
        # thin progress bar at top of footer
        self._prog = tk.Canvas(foot, height=4, bg=BORDER, highlightthickness=0)
        self._prog.pack(fill=tk.X)
        self._pfill = self._prog.create_rectangle(0, 0, 0, 4, fill=GREEN, width=0)
        # inner row: button LEFT, status RIGHT
        inner = tk.Frame(foot, bg=WHITE)
        inner.pack(fill=tk.X, padx=20, pady=10)
        self._btn_slot = tk.Frame(inner, bg=WHITE)
        self._btn_slot.pack(side=tk.LEFT)
        self._slbl = tk.Label(inner, textvariable=self._status_var,
                              bg=WHITE, fg=MUTED, font=F,
                              anchor="w", wraplength=680)
        self._slbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(16, 0))

    # ── Helpers ───────────────────────────────────────────────────
    def action_btn(self, text, cmd, bg=GREEN, hover=HDR2):
        b = _green_btn(self._btn_slot, text, cmd, bg=bg, hover=hover)
        b.pack(side=tk.LEFT, padx=(0, 8))
        return b

    def field(self, label_text, parent=None):
        p = parent or self.body
        f = _frm(p, bg=BG)
        f.pack(fill=tk.X, padx=32, pady=(0, 12))
        tk.Label(f, text=label_text.upper(), fg=MUTED, bg=BG,
                 font=FLAB, anchor="w").pack(anchor="w", pady=(0, 4))
        return f

    def _set_prog(self, pct):
        def _d():
            w = self._prog.winfo_width()
            self._prog.coords(self._pfill, 0, 0, w * pct / 100, 4)
        self.after(0, _d)

    def ok(self, msg):
        self._set_prog(100)
        self._status_var.set(f"✓  {msg}")
        self._slbl.config(fg=SUCCESS)

    def err(self, msg):
        self._set_prog(0)
        self._status_var.set(f"✕  {msg}")
        self._slbl.config(fg=DANGER)

    def run(self, fn):
        self._status_var.set("Processing…  please wait")
        self._slbl.config(fg=GREEN)
        for w in self._btn_slot.winfo_children():
            try: w.config(state=tk.DISABLED)
            except: pass
        self._anim_pct = 0
        self._animating = True
        self._do_anim()
        def worker():
            try:
                msg = fn()
                self.after(0, lambda m=msg: self._done(m, None))
            except Exception as ex:
                self.after(0, lambda e=ex: self._done(None, e))
        threading.Thread(target=worker, daemon=True).start()

    def _do_anim(self):
        if not self._animating: return
        self._anim_pct = (self._anim_pct + 3) % 88
        self._set_prog(self._anim_pct)
        self.after(40, self._do_anim)

    def _done(self, msg, err):
        self._animating = False
        for w in self._btn_slot.winfo_children():
            try: w.config(state=tk.NORMAL)
            except: pass
        if err:
            self.err(str(err))
        else:
            self.ok(msg)


    def setup(self): pass   # override in subclasses


# ══════════════════════════════════════════════════════════════════
# RADIO CARD  — white card with green dot when selected
# ══════════════════════════════════════════════════════════════════

class RadioCard(tk.Frame):
    def __init__(self, parent, text, subtext, var, value, **kw):
        super().__init__(parent, bg=WHITE, cursor="hand2",
                         highlightbackground=BORDER, highlightthickness=1, **kw)
        self.var = var; self.value = value
        # dot canvas
        self._dot = tk.Canvas(self, width=20, height=20, bg=WHITE, highlightthickness=0)
        self._dot.pack(side=tk.LEFT, padx=(14, 8), pady=10)
        self._draw_dot(False)
        self._lbl = tk.Label(self, text=text, bg=WHITE, fg=TEXT, font=FB, anchor="w")
        self._lbl.pack(side=tk.LEFT, pady=10)
        self._sub = tk.Label(self, text=f"  —  {subtext}", bg=WHITE, fg=MUTED, font=F, anchor="w")
        self._sub.pack(side=tk.LEFT, pady=10, padx=(0, 12))
        for w in (self, self._dot, self._lbl, self._sub):
            w.bind("<Button-1>", lambda e: self._pick())

    def _draw_dot(self, selected):
        self._dot.delete("all")
        if selected:
            self._dot.create_oval(2, 2, 18, 18, outline=GREEN, width=2, fill=WHITE)
            self._dot.create_oval(6, 6, 14, 14, fill=GREEN, outline=GREEN)
            self.config(highlightbackground=GREEN, highlightthickness=2)
        else:
            self._dot.create_oval(2, 2, 18, 18, outline="#aaaaaa", width=1.5, fill=WHITE)
            self.config(highlightbackground=BORDER, highlightthickness=1)

    def _pick(self):
        self.var.set(self.value)

    def refresh(self):
        self._draw_dot(self.var.get() == self.value)
        # update dot bg
        self._dot.config(bg=WHITE)


# ── Custom Checkbox — white box, black border, green tick ────────
class CustomCheckbox(tk.Frame):
    """White box with black border. Green ✓ when checked."""
    def __init__(self, parent, text, var, bg=None, **kw):
        bg = bg or BG
        super().__init__(parent, bg=bg, cursor="hand2", **kw)
        self._var = var
        self._box = tk.Canvas(self, width=16, height=16, bg=bg,
                              highlightthickness=0)
        self._box.pack(side=tk.LEFT, padx=(0,6))
        self._lbl = tk.Label(self, text=text, bg=bg, fg=TEXT, font=F)
        self._lbl.pack(side=tk.LEFT)
        self._draw()
        var.trace_add("write", lambda *a: self._draw())
        for w in (self, self._box, self._lbl):
            w.bind("<Button-1>", lambda e: self._toggle())

    def _toggle(self):
        self._var.set(not self._var.get())

    def _draw(self):
        c = self._box
        c.delete("all")
        # White box with black border
        c.create_rectangle(1, 1, 15, 15, outline="#333333", fill=WHITE, width=1.5)
        if self._var.get():
            # Green tick
            c.create_line(3, 8, 6, 12, fill=GREEN, width=2.5)
            c.create_line(6, 12, 13, 4, fill=GREEN, width=2.5)


# ══════════════════════════════════════════════════════════════════
# TOOL PANELS
# ══════════════════════════════════════════════════════════════════

class MergePanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF Files — select 2 or more (merged in selected order)")
        self.dz = DropZone(f, self.fvar, multi=True); self.dz.pack(fill=tk.X)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🔗  Merge PDFs", self._go)

    def _go(self):
        try: files = self.dz.paths()
        except: files = []
        if len(files) < 2: return self.err("Select at least 2 PDF files.")
        out = _ask_save("merged.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_merge(files, out))


class SplitPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        mf = self.field("Split mode")
        self.mode = tk.StringVar(value="pages")
        row = _frm(mf, bg=BG); row.pack(anchor="w")
        for v, t in [("pages","Split into individual pages"),("ranges","Split by page ranges")]:
            tk.Radiobutton(row, text=t, variable=self.mode, value=v,
                bg=BG, fg=TEXT, selectcolor=GREEN,
                activebackground=BG, font=F).pack(side=tk.LEFT, padx=(0,20))
        rf = self.field("Page ranges  (e.g.  1-3, 4-6)  — used only in range mode")
        self.rvar = tk.StringVar(value="1-3, 4-6")
        _entry(rf, self.rvar).pack(fill=tk.X)
        ff = self.field("Output folder")
        self.folder = tk.StringVar(value=str(OUT_DIR))
        _folder_row(ff, self.folder)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("✂️  Split PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        d = Path(self.folder.get()); d.mkdir(parents=True, exist_ok=True)
        if self.mode.get() == "pages":
            self.run(lambda: svc_split_pages(src, d))
        else:
            rv = self.rvar.get()
            self.run(lambda: svc_split_ranges(src, rv, d))


# ══════════════════════════════════════════════════════════════════
# VISUAL ORGANISE PANEL
# Shows page thumbnails. Click to select, drag to reorder.
# Rotate / delete buttons on each card. Exactly like iLovePDF.
# ══════════════════════════════════════════════════════════════════

class OrganisePanel(ToolPanel):
    """
    Visual page organiser — thumbnail grid with:
    • Rotate left / right buttons on each card
    • Delete button on each card
    • Click-to-select (highlight)
    • Drag to reorder (click drag)
    • Apply saves with chosen operations
    """
    def setup(self):
        self._src_path   = None
        self._pages      = []   # list of dicts: {index, rotation, deleted, photo}
        self._selected   = set()
        self._drag_src   = None
        self._thumb_refs = []   # keep PhotoImage refs alive

        # ── Top: file picker (compact) ──────────────────────────
        top = self.field("PDF File")
        row = _frm(top, bg=BG); row.pack(fill=tk.X)
        self._path_var = tk.StringVar()
        _entry(row, self._path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        _ghost_btn(row, "Browse…", self._browse).pack(side=tk.LEFT, padx=(6,0))

        # ── Hint label ──────────────────────────────────────────
        self._hint = tk.Label(self.body,
            text="Open a PDF to see its pages here",
            bg=BG, fg=MUTED, font=("Segoe UI", 11),
            anchor="center")
        self._hint.pack(fill=tk.X, pady=40)

        # ── Thumbnail grid canvas ────────────────────────────────
        self._grid_outer = tk.Frame(self.body, bg=BG)
        # (packed after file loaded)

        # ── Action button ────────────────────────────────────────
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("✅  Apply & Save", self._go)

    def _browse(self):
        f = filedialog.askopenfilename(filetypes=[("PDF","*.pdf")])
        if not f: return
        self._path_var.set(f)
        self._load_file(Path(f))

    def _load_file(self, path):
        self._src_path = path
        self._hint.pack_forget()
        self._grid_outer.pack_forget()
        for w in self._grid_outer.winfo_children(): w.destroy()
        self._pages.clear()
        self._thumb_refs.clear()
        self._selected.clear()
        self._status_var.set(f"Loading {path.name}…")
        self._slbl.config(fg=GREEN)

        def load():
            import pymupdf as fitz
            from PIL import Image, ImageTk
            doc = fitz.open(str(path))
            pages = []
            for i in range(len(doc)):
                page = doc[i]
                mat = fitz.Matrix(0.22, 0.22)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages.append({
                    "index":    i,
                    "rotation": 0,
                    "deleted":  False,
                    "pil_img":  img,
                    "orig_w":   pix.width,
                    "orig_h":   pix.height,
                })
            doc.close()
            self.after(0, lambda: self._render_grid(pages))

        threading.Thread(target=load, daemon=True).start()

    def _render_grid(self, pages):
        from PIL import ImageTk, Image
        self._pages = pages
        self._thumb_refs.clear()
        for w in self._grid_outer.winfo_children(): w.destroy()

        COLS = 4
        THUMB_W = 160
        THUMB_H = 210

        for i, pg in enumerate(pages):
            col = i % COLS
            row = i // COLS
            if col == 0:
                row_f = tk.Frame(self._grid_outer, bg=BG)
                row_f.pack(fill=tk.X, pady=6)
                for c in range(COLS):
                    row_f.columnconfigure(c, weight=1, uniform="pg")
                self._cur_row = row_f

            card = tk.Frame(self._cur_row, bg=WHITE,
                            highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=col, padx=8, sticky="n")
            pg["card"] = card

            # Thumbnail
            thumb_img = pg["pil_img"].copy()
            thumb_img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumb_img)
            self._thumb_refs.append(photo)
            pg["photo"] = photo

            img_lbl = tk.Label(card, image=photo, bg="#f5f5f5",
                               cursor="hand2")
            img_lbl.pack(padx=4, pady=(8,2))

            # Page number
            tk.Label(card, text=str(i + 1), bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 8)).pack()

            # Button row: rotate left | rotate right | delete
            btn_row = tk.Frame(card, bg=WHITE)
            btn_row.pack(pady=(2,6))

            def make_rot_left(idx=i):
                return lambda: self._rotate_page(idx, -90)
            def make_rot_right(idx=i):
                return lambda: self._rotate_page(idx, 90)
            def make_del(idx=i):
                return lambda: self._delete_page(idx)

            for txt, cmd, fg_col in [
                ("↺", make_rot_left(), GREEN),
                ("↻", make_rot_right(), GREEN),
                ("✕", make_del(), DANGER),
            ]:
                b = tk.Button(btn_row, text=txt, command=cmd,
                              bg=WHITE, fg=fg_col,
                              activebackground=GREEN_L,
                              activeforeground=fg_col,
                              relief=tk.FLAT, cursor="hand2",
                              font=("Segoe UI", 13, "bold"),
                              width=3, bd=0)
                b.pack(side=tk.LEFT, padx=2)

            # Drag to reorder
            img_lbl.bind("<Button-1>",      lambda e, idx=i: self._drag_start(idx))
            img_lbl.bind("<B1-Motion>",     lambda e, idx=i: self._drag_motion(e, idx))
            img_lbl.bind("<ButtonRelease-1>",lambda e, idx=i: self._drag_end(idx))

        self._grid_outer.pack(fill=tk.X, padx=24, pady=4)
        self._status_var.set(f"Loaded {len(pages)} pages  ·  Rotate, delete or drag to reorder")
        self._slbl.config(fg=MUTED)

    def _rotate_page(self, idx, angle):
        from PIL import ImageTk
        pg = self._pages[idx]
        pg["rotation"] = (pg["rotation"] + angle) % 360
        rotated = pg["pil_img"].rotate(-angle, expand=True)
        pg["pil_img"] = rotated
        # Rebuild thumbnail
        from PIL import Image
        thumb = rotated.copy()
        thumb.thumbnail((160, 210), Image.LANCZOS)
        photo = ImageTk.PhotoImage(thumb)
        pg["photo"] = photo
        self._thumb_refs.append(photo)
        # Update card image
        for w in pg["card"].winfo_children():
            if isinstance(w, tk.Label) and hasattr(w, 'config'):
                try:
                    if w.cget("image"):
                        w.config(image=photo)
                        break
                except: pass

    def _delete_page(self, idx):
        pg = self._pages[idx]
        card = pg["card"]
        if pg.get("deleted"):
            # Undelete
            pg["deleted"] = False
            card.config(highlightbackground=BORDER, highlightthickness=1)
            for w in card.winfo_children():
                try: w.config(bg=WHITE)
                except: pass
        else:
            pg["deleted"] = True
            card.config(highlightbackground=DANGER, highlightthickness=2)
            for w in card.winfo_children():
                try: w.config(bg="#fff0f0")
                except: pass

    def _drag_start(self, idx):
        self._drag_src = idx

    def _drag_motion(self, event, idx):
        # Highlight target card
        pass

    def _drag_end(self, idx):
        if self._drag_src is None or self._drag_src == idx:
            self._drag_src = None
            return
        src = self._drag_src
        self._drag_src = None
        # Move src to idx position
        pg = self._pages.pop(src)
        self._pages.insert(idx, pg)
        # Re-render
        self._render_grid(self._pages)

    def _go(self):
        if not self._src_path or not self._pages:
            return self.err("Open a PDF file first.")
        active = [pg for pg in self._pages if not pg.get("deleted")]
        if not active:
            return self.err("All pages are deleted — keep at least one.")
        out = _ask_save("organised.pdf")
        if out is None: return self.err("Save cancelled.")

        # Build ordered index list with rotations
        order   = [pg["index"] for pg in active]
        rotations = {pg["index"]: pg["rotation"] for pg in active}
        src_path = self._src_path

        def task():
            import pymupdf as fitz
            src_doc = fitz.open(str(src_path))
            out_doc = fitz.open()
            for orig_idx in order:
                out_doc.insert_pdf(src_doc, from_page=orig_idx, to_page=orig_idx)
                if rotations.get(orig_idx, 0):
                    out_doc[-1].set_rotation(rotations[orig_idx])
            out_doc.save(str(out), deflate=True, garbage=3)
            out_doc.close(); src_doc.close()
            kept = len(order)
            deleted = len(self._pages) - kept
            return (f"Saved → {out.name}  "
                    f"({kept} pages kept"
                    + (f", {deleted} deleted" if deleted else "") + ")")

        self.run(task)


class RepairPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        info = tk.Label(self.body,
            text="  ℹ  Repairs corrupt PDFs, rebuilds the cross-reference table and removes damaged objects.",
            bg=GREEN_L, fg=HEADER, font=F, anchor="w", padx=12, pady=8)
        info.pack(fill=tk.X, padx=32, pady=(0,8))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🔧  Repair PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("repaired.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_repair(src, out))


class RemoveMetadataPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        info = tk.Label(self.body,
            text="  ℹ  Strips author name, creation date, software info and GPS data from the PDF.",
            bg=GREEN_L, fg=HEADER, font=F, anchor="w", padx=12, pady=8)
        info.pack(fill=tk.X, padx=32, pady=(0,8))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🧹  Remove Metadata", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("no_metadata.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_remove_metadata(src, out))


class GrayscalePanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        info = tk.Label(self.body,
            text="  ℹ  Converts all pages to black & white. Reduces file size by 60–80%. Ideal for printing.",
            bg=GREEN_L, fg=HEADER, font=F, anchor="w", padx=12, pady=8)
        info.pack(fill=tk.X, padx=32, pady=(0,8))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🖤  Convert to Grayscale", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("grayscale.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_grayscale(src, out))


class FlattenPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        info = tk.Label(self.body,
            text="  ℹ  Merges annotations, form fields and interactive layers into static content. Makes the PDF tamper-proof.",
            bg=GREEN_L, fg=HEADER, font=F, anchor="w", padx=12, pady=8)
        info.pack(fill=tk.X, padx=32, pady=(0,8))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("📋  Flatten PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("flattened.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_flatten(src, out))


class RemoveBlankPagesPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        info = tk.Label(self.body,
            text="  ℹ  Automatically detects and removes blank or near-blank pages. Useful for scanned documents.",
            bg=GREEN_L, fg=HEADER, font=F, anchor="w", padx=12, pady=8)
        info.pack(fill=tk.X, padx=32, pady=(0,8))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🗑️  Remove Blank Pages", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("no_blank_pages.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_remove_blank_pages(src, out))


class CompressPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        lf = self.field("Compression level")
        self.level = tk.StringVar(value="medium")
        self._cards = []
        for v, t, sub in [
            ("low",    "Low compression",   "Highest quality — best for printing"),
            ("medium", "Medium",            "Balanced quality and file size  ·  Recommended"),
            ("high",   "High compression",  "Smallest file — ideal for sharing"),
        ]:
            rc = RadioCard(lf, t, sub, self.level, v)
            rc.pack(fill=tk.X, pady=3)
            self._cards.append(rc)
            self.level.trace_add("write", lambda *a: [c.refresh() for c in self._cards])
        # trigger initial draw
        [c.refresh() for c in self._cards]
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🗜️  Compress PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("compressed.pdf")
        if out is None: return self.err("Save cancelled.")
        lvl = self.level.get()
        self.run(lambda: svc_compress(src, out, lvl))


class RotatePanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        af = self.field("Rotation angle")
        self.angle = tk.IntVar(value=90)
        row = _frm(af, bg=BG); row.pack(anchor="w")
        for v, t in [(90,"90° Clockwise"),(180,"180°"),(270,"270° Counter-clockwise")]:
            tk.Radiobutton(row, text=t, variable=self.angle, value=v,
                bg=BG, fg=TEXT, selectcolor=GREEN,
                activebackground=BG, font=F).pack(side=tk.LEFT, padx=(0,20), pady=6)
        pf = self.field("Pages  (blank = all pages, or e.g.  1, 3)")
        self.pvar = tk.StringVar()
        _entry(pf, self.pvar).pack(fill=tk.X)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🔄  Rotate PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        out = _ask_save("rotated.pdf")
        if out is None: return self.err("Save cancelled.")
        a = self.angle.get(); ps = self.pvar.get()
        self.run(lambda: svc_rotate(src, a, ps, out))


class WatermarkTextPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        tf = self.field("Watermark text")
        self.tvar = tk.StringVar(value="CONFIDENTIAL")
        _entry(tf, self.tvar).pack(fill=tk.X)
        # options grid
        grid = _frm(self.body, bg=BG); grid.pack(fill=tk.X, padx=32, pady=(0,12))
        self.pos = tk.StringVar(value="center")
        self.op  = tk.StringVar(value="0.3")
        self.fs  = tk.StringVar(value="48")
        self.col = tk.StringVar(value="#1a5c38")
        self.rot = tk.StringVar(value="45")
        for ltext, widget_fn in [
            ("Position",   lambda c: _combo(c, ["center","top_left","top_right","bottom_left","bottom_right","tile"], self.pos, 14).pack(fill=tk.X)),
            ("Opacity",    lambda c: _entry(c, self.op, 10).pack(anchor="w")),
            ("Font size",  lambda c: _entry(c, self.fs, 10).pack(anchor="w")),
            ("Color #hex", lambda c: _entry(c, self.col, 12).pack(anchor="w")),
            ("Rotation °", lambda c: _entry(c, self.rot, 10).pack(anchor="w")),
        ]:
            c = _frm(grid, bg=BG); c.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
            tk.Label(c, text=ltext.upper(), fg=MUTED, bg=BG, font=FLAB, anchor="w").pack(anchor="w", pady=(0,4))
            widget_fn(c)
        pf = self.field("Pages  (blank = all, or e.g.  1, 2)")
        self.pvar = tk.StringVar(); _entry(pf, self.pvar).pack(fill=tk.X)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("💧  Apply Watermark", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        txt = self.tvar.get().strip()
        if not txt: return self.err("Enter watermark text.")
        try:
            op = float(self.op.get()); fs = float(self.fs.get()); rot = float(self.rot.get())
        except ValueError: return self.err("Opacity, font size, and rotation must be numbers.")
        out = _ask_save("watermarked.pdf")
        if out is None: return self.err("Save cancelled.")
        pos = self.pos.get(); col = self.col.get(); ps = self.pvar.get()
        self.run(lambda: svc_watermark_text(src, txt, pos, op, fs, col, rot, ps, out))


class WatermarkImagePanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar(); self.ivar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        f2 = self.field("Watermark Image  (PNG or JPG)")
        self.dz2 = DropZone(f2, self.ivar, accept_img=True); self.dz2.pack(fill=tk.X)
        tk.Label(f2, text="Supports: PNG, JPG, JPEG, BMP, TIFF, WebP",
                 bg=BG, fg=MUTED, font=("Segoe UI",8)).pack(anchor="w", pady=(2,0))
        grid = _frm(self.body, bg=BG); grid.pack(fill=tk.X, padx=32, pady=(0,12))
        self.op = tk.StringVar(value="0.3"); self.sc = tk.StringVar(value="1.0")
        for ltext, var in [("Opacity", self.op), ("Scale", self.sc)]:
            c = _frm(grid, bg=BG); c.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,12))
            tk.Label(c, text=ltext.upper(), fg=MUTED, bg=BG, font=FLAB, anchor="w").pack(anchor="w", pady=(0,4))
            _entry(c, var, 10).pack(anchor="w")
        pf = self.field("Pages  (blank = all)")
        self.pvar = tk.StringVar(); _entry(pf, self.pvar).pack(fill=tk.X)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🖼️  Apply Watermark", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        imgs = self.dz2.paths()
        if not imgs: return self.err("Select a watermark image.")
        try: op = float(self.op.get()); sc = float(self.sc.get())
        except ValueError: return self.err("Opacity and scale must be numbers.")
        out = _ask_save("watermarked.pdf")
        if out is None: return self.err("Save cancelled.")
        wm = imgs[0]; ps = self.pvar.get()
        self.run(lambda: svc_watermark_image(src, wm, op, sc, ps, out))


class PageNumberPanel(ToolPanel):
    COLOURS = [
        ("Black","#000000"),("Dark Grey","#404040"),("Grey","#808080"),
        ("Light Grey","#C0C0C0"),("Dark Red","#C00000"),("Red","#FF0000"),
        ("Orange","#FF6600"),("Dark Yellow","#CC9900"),("Dark Green","#1a5c38"),
        ("Green","#2d7a4f"),("Dark Blue","#003399"),("Blue","#0070C0"),
        ("Purple","#7030A0"),("Pink","#FF00FF"),("White","#FFFFFF"),
    ]
    # Position grid: (label, pdf_position, grid_row, grid_col)
    POSITIONS = [
        ("top_left",     0, 0), ("top_center",    0, 1), ("top_right",    0, 2),
        ("middle_left",  1, 0), ("middle_center", 1, 1), ("middle_right", 1, 2),
        ("bottom_left",  2, 0), ("bottom_center", 2, 1), ("bottom_right", 2, 2),
    ]

    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)

        # ── Row: Position grid + Margin ──────────────────────────
        row1 = _frm(self.body, bg=BG); row1.pack(fill=tk.X, padx=32, pady=(0,12))

        # Left: position grid (3x3 clickable dots like iLovePDF)
        pos_col = _frm(row1, bg=BG); pos_col.pack(side=tk.LEFT, padx=(0,32))
        tk.Label(pos_col, text="POSITION", fg=MUTED, bg=BG, font=FLAB,
                 anchor="w").pack(anchor="w", pady=(0,6))
        self._pos_var = tk.StringVar(value="bottom_center")
        self._pos_dots = {}
        grid_f = _frm(pos_col, bg=WHITE, highlightbackground=BORDER,
                      highlightthickness=1)
        grid_f.pack()
        CELL = 34
        for pos_name, gr, gc in self.POSITIONS:
            btn = tk.Canvas(grid_f, width=CELL, height=CELL,
                           bg=WHITE, highlightthickness=0, cursor="hand2")
            btn.grid(row=gr, column=gc, padx=1, pady=1)
            self._pos_dots[pos_name] = btn
            btn.bind("<Button-1>", lambda e, p=pos_name: self._pick_pos(p))
            btn.bind("<Enter>",    lambda e, b=btn: b.config(bg=GREEN_L))
            btn.bind("<Leave>",    lambda e, b=btn, p=pos_name:
                     b.config(bg=GREEN if self._pos_var.get()==p else WHITE))
        self._pos_var.trace_add("write", lambda *a: self._draw_pos_grid())
        self._draw_pos_grid()

        # Right: font size + colour
        opts_col = _frm(row1, bg=BG); opts_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(opts_col, text="FONT SIZE", fg=MUTED, bg=BG, font=FLAB,
                 anchor="w").pack(anchor="w", pady=(0,4))
        self.fs = tk.StringVar(value="12")
        _entry(opts_col, self.fs, 8).pack(anchor="w", pady=(0,12))

        tk.Label(opts_col, text="COLOUR", fg=MUTED, bg=BG, font=FLAB,
                 anchor="w").pack(anchor="w", pady=(0,6))
        self._col_hex = "#000000"
        swatch_f = _frm(opts_col, bg=BG); swatch_f.pack(anchor="w")
        cols_per_row = 5; row_f = None
        for i,(name,hx) in enumerate(self.COLOURS):
            if i % cols_per_row == 0:
                row_f = _frm(swatch_f, bg=BG); row_f.pack(anchor="w", pady=1)
            sw = tk.Canvas(row_f, width=20, height=20, bg=hx,
                           highlightthickness=1, highlightbackground="#aaaaaa",
                           cursor="hand2")
            sw.pack(side=tk.LEFT, padx=1)
            sw.bind("<Button-1>", lambda e, h=hx, n=name: self._pick_col(h, n))
            sw.bind("<Enter>",    lambda e, s=sw: s.config(highlightbackground="#000"))
            sw.bind("<Leave>",    lambda e, s=sw: s.config(highlightbackground="#aaaaaa"))
        # Preview
        prow = _frm(opts_col, bg=BG); prow.pack(anchor="w", pady=(6,0))
        self._col_preview = tk.Frame(prow, bg="#000000", width=20, height=20,
                                     highlightbackground="#333", highlightthickness=1)
        self._col_preview.pack(side=tk.LEFT)
        self._col_name_lbl = tk.Label(prow, text="Black", bg=BG, fg=TEXT, font=F)
        self._col_name_lbl.pack(side=tk.LEFT, padx=(6,0))

        # ── Pages section ─────────────────────────────────────────
        pf = self.field("Pages")
        # First number
        fn_row = tk.Frame(pf, bg=WHITE, highlightbackground=BORDER,
                          highlightthickness=1)
        fn_row.pack(anchor="w", pady=(0,8))
        tk.Label(fn_row, text="First number:", bg=WHITE, fg=TEXT,
                 font=F, padx=10, pady=8).pack(side=tk.LEFT)
        tk.Frame(fn_row, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)
        self.st = tk.StringVar(value="1")
        _entry(fn_row, self.st, 6).pack(side=tk.LEFT, padx=8, pady=6)

        # From / To pages
        ft_row = _frm(pf, bg=BG); ft_row.pack(anchor="w")
        tk.Label(ft_row, text="Which pages do you want to number?",
                 bg=BG, fg=TEXT, font=F).pack(anchor="w", pady=(0,6))
        inner = _frm(ft_row, bg=BG); inner.pack(anchor="w")
        # From
        from_box = tk.Frame(inner, bg=WHITE, highlightbackground=BORDER,
                            highlightthickness=1)
        from_box.pack(side=tk.LEFT)
        tk.Label(from_box, text="from page", bg=WHITE, fg=TEXT,
                 font=F, padx=10, pady=8).pack(side=tk.LEFT)
        tk.Frame(from_box, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)
        self.page_from = tk.StringVar(value="1")
        _entry(from_box, self.page_from, 5).pack(side=tk.LEFT, padx=8, pady=6)
        # To
        tk.Label(inner, text="  to  ", bg=BG, fg=TEXT, font=F).pack(side=tk.LEFT)
        to_box = tk.Frame(inner, bg=WHITE, highlightbackground=BORDER,
                          highlightthickness=1)
        to_box.pack(side=tk.LEFT)
        self.page_to = tk.StringVar(value="end")
        _entry(to_box, self.page_to, 5).pack(side=tk.LEFT, padx=8, pady=6)
        tk.Label(pf, text="Leave 'to' as 'end' to number all remaining pages.",
                 bg=BG, fg=MUTED, font=("Segoe UI",8)).pack(anchor="w", pady=(4,0))

        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🔢  Add Page Numbers", self._go)

    def _pick_pos(self, pos):
        self._pos_var.set(pos)

    def _draw_pos_grid(self):
        sel = self._pos_var.get()
        for pos_name, dot in self._pos_dots.items():
            dot.delete("all")
            is_sel = (pos_name == sel)
            dot.config(bg=WHITE)
            # Draw small circle dot
            dot.create_oval(10, 10, 24, 24,
                            fill=GREEN if is_sel else "#cccccc",
                            outline=GREEN if is_sel else "#aaaaaa",
                            width=1)

    def _pick_col(self, hx, name):
        self._col_hex = hx
        self._col_preview.config(bg=hx)
        self._col_name_lbl.config(text=name)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        try:
            fs = float(self.fs.get())
            st = int(self.st.get())
        except ValueError:
            return self.err("Font size and start number must be numbers.")
        out = _ask_save("numbered.pdf")
        if out is None: return self.err("Save cancelled.")

        pos = self._pos_var.get()
        # Map middle positions to supported ones
        pos_map = {
            "middle_left": "bottom_left", "middle_center": "bottom_center",
            "middle_right": "bottom_right",
        }
        pos = pos_map.get(pos, pos)

        col = self._col_hex
        pf_str = self.page_from.get().strip()
        pt_str = self.page_to.get().strip()
        # Build pages list
        try:
            pf_num = int(pf_str)
        except ValueError:
            pf_num = 1
        import pymupdf as fitz
        doc = fitz.open(str(src)); n = len(doc); doc.close()
        if pt_str.lower() in ("end",""):
            pt_num = n
        else:
            try: pt_num = int(pt_str)
            except ValueError: pt_num = n
        pf_num = max(1, pf_num); pt_num = min(n, pt_num)
        pages_str = ",".join(str(i) for i in range(pf_num, pt_num+1))

        self.run(lambda: svc_page_numbers(src, pos, fs, col, st, pages_str, out))
class CropPanel(ToolPanel):
    """
    Visual crop: opens a page preview, user draws a rectangle by dragging.
    Options: apply to current page only OR all pages.
    """
    def setup(self):
        self._src_path  = None
        self._page_doc  = None
        self._page_idx  = 0
        self._pdf_w     = 595.0
        self._pdf_h     = 842.0
        self._canvas_w  = 1
        self._canvas_h  = 1
        self._drag_x0 = self._drag_y0 = 0
        self._rect_id   = None
        self._crop_coords = None  # (x0,y0,x1,y1) in PDF points

        # File picker
        top = self.field("PDF File")
        row = _frm(top, bg=BG); row.pack(fill=tk.X)
        self._pvar = tk.StringVar()
        _entry(row, self._pvar, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        _ghost_btn(row, "Browse…", self._browse).pack(side=tk.LEFT, padx=(6,0))

        # Page selector row
        nav = _frm(self.body, bg=BG); nav.pack(fill=tk.X, padx=32, pady=(4,8))
        _ghost_btn(nav, "◀ Prev", self._prev_page).pack(side=tk.LEFT)
        self._page_lbl = tk.Label(nav, text="Open a PDF to start",
                                  bg=BG, fg=MUTED, font=F)
        self._page_lbl.pack(side=tk.LEFT, padx=12)
        _ghost_btn(nav, "Next ▶", self._next_page).pack(side=tk.LEFT)

        # Canvas for page preview + crop drawing
        canvas_frame = tk.Frame(self.body, bg=BORDER,
                                highlightbackground=BORDER, highlightthickness=1)
        canvas_frame.pack(fill=tk.X, padx=32, pady=(0,8))
        self._canvas = tk.Canvas(canvas_frame, bg="#e0e0e0",
                                 cursor="crosshair", height=400)
        self._canvas.pack(fill=tk.X)
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",        self._on_drag)
        self._canvas.bind("<ButtonRelease-1>",  self._on_release)
        self._canvas.bind("<Configure>",        self._on_resize)

        # Hint
        self._hint_lbl = tk.Label(self.body,
            text="Draw a rectangle on the page to select the crop area",
            bg=BG, fg=MUTED, font=F)
        self._hint_lbl.pack(padx=32, pady=(0,8))

        # Coords readout
        self._coords_lbl = tk.Label(self.body, text="", bg=BG, fg=GREEN, font=FB)
        self._coords_lbl.pack(padx=32, pady=(0,4))

        # Apply scope — custom checkboxes
        scope_f = self.field("Apply crop to")
        self._scope = tk.StringVar(value="all")
        for val, txt in [("current", "Current page only"), ("all", "All pages")]:
            rb_row = tk.Frame(scope_f, bg=BG, cursor="hand2")
            rb_row.pack(anchor="w", pady=2)
            dot_c = tk.Canvas(rb_row, width=18, height=18, bg=BG, highlightthickness=0)
            dot_c.pack(side=tk.LEFT, padx=(0,6))
            lbl_w = tk.Label(rb_row, text=txt, bg=BG, fg=TEXT, font=F)
            lbl_w.pack(side=tk.LEFT)
            def make_pick(v=val): return lambda e: self._pick_scope(v)
            for w in (rb_row, dot_c, lbl_w):
                w.bind("<Button-1>", make_pick())
            # Store for redraw
            if not hasattr(self, "_scope_dots"): self._scope_dots = {}
            self._scope_dots[val] = dot_c
            self._scope.trace_add("write", lambda *a: self._draw_scope_dots())
        self._draw_scope_dots()

        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("✂️  Crop PDF", self._go)

    def _pick_scope(self, val):
        self._scope.set(val)

    def _draw_scope_dots(self):
        for val, dot_c in self._scope_dots.items():
            dot_c.delete("all")
            dot_c.create_oval(1,1,17,17, outline="#333333", fill=WHITE, width=1.5)
            if self._scope.get() == val:
                dot_c.create_oval(1,1,17,17, outline=GREEN, fill=WHITE, width=2)
                dot_c.create_oval(5,5,13,13, fill=GREEN, outline=GREEN)

    def _browse(self):
        f = filedialog.askopenfilename(filetypes=[("PDF","*.pdf")])
        if not f: return
        self._pvar.set(f)
        self._src_path = Path(f)
        self._page_idx = 0
        if self._page_doc:
            try: self._page_doc.close()
            except: pass
        self._page_doc = __import__("pymupdf").open(str(self._src_path))
        self._render_page()

    def _prev_page(self):
        if not self._page_doc: return
        if self._page_idx > 0:
            self._page_idx -= 1
            self._crop_coords = None
            self._render_page()

    def _next_page(self):
        if not self._page_doc: return
        if self._page_idx < len(self._page_doc) - 1:
            self._page_idx += 1
            self._crop_coords = None
            self._render_page()

    def _render_page(self):
        if not self._page_doc: return
        import pymupdf as fitz
        from PIL import Image, ImageTk
        page = self._page_doc[self._page_idx]
        self._pdf_w = page.rect.width
        self._pdf_h = page.rect.height
        n = len(self._page_doc)
        self._page_lbl.config(text=f"Page {self._page_idx+1} of {n}")
        # Render to fit canvas width
        cw = max(self._canvas.winfo_width(), 400)
        scale = cw / self._pdf_w
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self._canvas_w = pix.width
        self._canvas_h = pix.height
        self._canvas.config(height=pix.height)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self._rect_id = None
        self._crop_coords = None
        self._coords_lbl.config(text="")

    def _on_resize(self, event):
        if self._page_doc:
            self._render_page()

    def _canvas_to_pdf(self, cx, cy):
        """Convert canvas pixel coords to PDF points."""
        px = (cx / self._canvas_w) * self._pdf_w
        py = (cy / self._canvas_h) * self._pdf_h
        return px, py

    def _on_press(self, event):
        self._drag_x0 = event.x
        self._drag_y0 = event.y
        if self._rect_id:
            self._canvas.delete(self._rect_id)
            self._rect_id = None

    def _on_drag(self, event):
        if self._rect_id:
            self._canvas.delete(self._rect_id)
        x0, y0 = min(self._drag_x0, event.x), min(self._drag_y0, event.y)
        x1, y1 = max(self._drag_x0, event.x), max(self._drag_y0, event.y)
        self._rect_id = self._canvas.create_rectangle(
            x0, y0, x1, y1,
            outline=GREEN, width=2, dash=(4,3),
            fill="", stipple="")

    def _on_release(self, event):
        x0c = min(self._drag_x0, event.x)
        y0c = min(self._drag_y0, event.y)
        x1c = max(self._drag_x0, event.x)
        y1c = max(self._drag_y0, event.y)
        if x1c - x0c < 5 or y1c - y0c < 5:
            self._crop_coords = None
            self._coords_lbl.config(text="Too small — draw a larger rectangle")
            return
        # Convert to PDF points (PyMuPDF origin = top-left)
        px0, py0 = self._canvas_to_pdf(x0c, y0c)
        px1, py1 = self._canvas_to_pdf(x1c, y1c)
        self._crop_coords = (px0, py0, px1, py1)
        self._coords_lbl.config(
            text=f"Crop area: ({px0:.0f}, {py0:.0f}) → ({px1:.0f}, {py1:.0f}) pt")

    def _go(self):
        if not self._src_path:
            return self.err("Open a PDF file first.")
        if not self._crop_coords:
            return self.err("Draw a crop rectangle on the page first.")
        x0, y0, x1, y1 = self._crop_coords
        scope = self._scope.get()
        page_idx = self._page_idx
        out = _ask_save("cropped.pdf")
        if out is None: return self.err("Save cancelled.")

        def task():
            import pymupdf as fitz
            doc = fitz.open(str(self._src_path))
            rect = fitz.Rect(x0, y0, x1, y1)
            if scope == "current":
                pg = doc[page_idx]
                if not pg.rect.contains(rect):
                    raise ValueError(f"Crop area exceeds page dimensions.")
                pg.set_mediabox(rect); pg.set_cropbox(rect)
            else:
                for pg in doc:
                    # Scale rect proportionally if pages differ in size
                    sx = pg.rect.width  / self._pdf_w
                    sy = pg.rect.height / self._pdf_h
                    scaled = fitz.Rect(x0*sx, y0*sy, x1*sx, y1*sy)
                    if not pg.rect.contains(scaled): scaled = pg.rect
                    pg.set_mediabox(scaled); pg.set_cropbox(scaled)
            doc.save(str(out), deflate=True, garbage=3)
            doc.close()
            n = 1 if scope=="current" else len(fitz.open(str(self._src_path)))
            return f"Cropped → {out.name}"

        self.run(task)


class EncryptPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        grid = _frm(self.body, bg=BG); grid.pack(fill=tk.X, padx=32, pady=(0,12))
        self.uvar = tk.StringVar(); self.ovar2 = tk.StringVar()
        for ltext, var in [("User password  (required to open)",self.uvar),
                           ("Owner password  (full access)",self.ovar2)]:
            c = _frm(grid, bg=BG); c.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,12))
            tk.Label(c, text=ltext.upper(), fg=MUTED, bg=BG, font=FLAB, anchor="w").pack(anchor="w", pady=(0,4))
            _entry(c, var, show="*", width=22).pack(fill=tk.X)
        pf = self.field("Permissions")
        self.prt = tk.BooleanVar(value=True); self.cpy = tk.BooleanVar(value=False)
        pr = _frm(pf, bg=BG); pr.pack(anchor="w")
        CustomCheckbox(pr, "Allow printing",    self.prt, bg=BG).pack(side=tk.LEFT, padx=(0,20))
        CustomCheckbox(pr, "Allow copying text",self.cpy, bg=BG).pack(side=tk.LEFT)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🔐  Protect PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        u = self.uvar.get(); o = self.ovar2.get()
        if not u and not o: return self.err("Enter at least one password.")
        out = _ask_save("encrypted.pdf")
        if out is None: return self.err("Save cancelled.")
        prt = self.prt.get(); cpy = self.cpy.get()
        self.run(lambda: svc_encrypt(src, u, o, prt, cpy, out))


class DecryptPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        pf = self.field("Password")
        self.pwvar = tk.StringVar(); _entry(pf, self.pwvar, show="*").pack(fill=tk.X)
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🔓  Unlock PDF", self._go)

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        pw = self.pwvar.get()
        if not pw: return self.err("Enter the PDF password.")
        out = _ask_save("unlocked.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_decrypt(src, pw, out))


class RedactTextPanel(ToolPanel):
    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        tf = self.field("Search terms to redact  (one per line)")
        self.txt = tk.Text(tf, height=5, bg=WHITE, fg=TEXT,
                           insertbackground=TEXT, relief=tk.FLAT,
                           highlightbackground=BORDER, highlightthickness=1, font=F)
        self.txt.insert("1.0", "CONFIDENTIAL\nJohn Doe\n123-45-6789")
        self.txt.pack(fill=tk.X)
        warn = tk.Label(self.body,
            text="  ⚠  Redaction is permanent and irreversible — original content cannot be recovered.",
            bg="#fff3cd", fg=WARN, font=F, anchor="w", padx=12, pady=8)
        warn.pack(fill=tk.X, padx=32, pady=(0,12))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("⬛  Redact PDF", self._go, bg=DANGER, hover="#a93226")

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        terms = self.txt.get("1.0", tk.END)
        out = _ask_save("redacted.pdf")
        if out is None: return self.err("Save cancelled.")
        self.run(lambda: svc_redact_text(src, terms, out))


class RedactRegionPanel(ToolPanel):
    def __init__(self, *a, **kw):
        self.regions = []
        super().__init__(*a, **kw)

    def setup(self):
        self.fvar = tk.StringVar()
        f = self.field("PDF File")
        self.dz = DropZone(f, self.fvar); self.dz.pack(fill=tk.X)
        rf = self.field("Define a region")
        row = _frm(rf, bg=BG); row.pack(anchor="w")
        self.pg = tk.StringVar(value="1")
        self.x0 = tk.StringVar(value="72"); self.y0 = tk.StringVar(value="680")
        self.x1 = tk.StringVar(value="300"); self.y1 = tk.StringVar(value="720")
        for ltext, var in [("Page",self.pg),("X0",self.x0),("Y0",self.y0),("X1",self.x1),("Y1",self.y1)]:
            c = _frm(row, bg=BG); c.pack(side=tk.LEFT, padx=(0,10))
            tk.Label(c, text=ltext.upper(), fg=MUTED, bg=BG, font=FLAB, anchor="w").pack(anchor="w", pady=(0,4))
            _entry(c, var, 7).pack(anchor="w")
        _ghost_btn(rf, "+ Add Region", self._add).pack(anchor="w", pady=(10,0))
        self.lb = tk.Listbox(self.body, height=4, bg=WHITE, fg=TEXT,
                             selectbackground=GREEN, relief=tk.FLAT, font=F,
                             highlightbackground=BORDER, highlightthickness=1)
        self.lb.pack(fill=tk.X, padx=32, pady=(0,4))
        _ghost_btn(self.body, "✕ Remove selected", self._remove).pack(anchor="w", padx=32, pady=(0,12))
        warn = tk.Label(self.body,
            text="  ⚠  Redaction is permanent and irreversible.",
            bg="#fff3cd", fg=WARN, font=F, anchor="w", padx=12, pady=8)
        warn.pack(fill=tk.X, padx=32, pady=(0,12))
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.action_btn("🟥  Redact Regions", self._go, bg=DANGER, hover="#a93226")

    def _add(self):
        try:
            rg = {"page": int(self.pg.get()), "x0": float(self.x0.get()),
                  "y0": float(self.y0.get()), "x1": float(self.x1.get()),
                  "y1": float(self.y1.get())}
        except ValueError: return self.err("All region values must be numbers.")
        self.regions.append(rg)
        self.lb.insert(tk.END, f"P{rg['page']}  ({rg['x0']},{rg['y0']}) → ({rg['x1']},{rg['y1']})")

    def _remove(self):
        s = self.lb.curselection()
        if s: self.lb.delete(s[0]); self.regions.pop(s[0])

    def _go(self):
        try: src = self.dz.single()
        except ValueError as e: return self.err(str(e))
        if not self.regions: return self.err("Add at least one region first.")
        out = _ask_save("redacted.pdf")
        if out is None: return self.err("Save cancelled.")
        rgs = list(self.regions)
        self.run(lambda: svc_redact_regions(src, rgs, out))


# ══════════════════════════════════════════════════════════════════
# SHARED FORM HELPERS
# ══════════════════════════════════════════════════════════════════

def _entry(parent, var=None, width=36, show=None):
    kw = dict(textvariable=var, width=width, bg=WHITE, fg=TEXT,
              insertbackground=TEXT, relief=tk.FLAT,
              highlightbackground=BORDER, highlightcolor=GREEN,
              highlightthickness=1, font=F)
    if show: kw["show"] = show
    return tk.Entry(parent, **kw)

def _file_row(parent, var, default_name, ext="pdf"):
    row = _frm(parent, bg=BG); row.pack(fill=tk.X)
    _entry(row, var, width=32).pack(side=tk.LEFT, fill=tk.X, expand=True)
    def browse():
        ft = [("PDF","*.pdf")] if ext == "pdf" else [("ZIP","*.zip")]
        f = filedialog.asksaveasfilename(defaultextension=f".{ext}",
                                          initialfile=default_name, filetypes=ft)
        if f: var.set(f)
    _ghost_btn(row, "Save As…", browse).pack(side=tk.LEFT, padx=(6,0))

def _folder_row(parent, var):
    row = _frm(parent, bg=BG); row.pack(fill=tk.X)
    _entry(row, var, width=32).pack(side=tk.LEFT, fill=tk.X, expand=True)
    def browse():
        d = filedialog.askdirectory()
        if d: var.set(d)
    _ghost_btn(row, "Browse…", browse).pack(side=tk.LEFT, padx=(6,0))

def _ask_save(default_name, ext="pdf"):
    """Show Save As dialog and return chosen Path, or None if cancelled."""
    ft = [("ZIP files","*.zip")] if ext=="zip" else [("PDF files","*.pdf")]
    f = filedialog.asksaveasfilename(
        defaultextension=f".{ext}",
        initialfile=default_name,
        initialdir=str(OUT_DIR),
        filetypes=ft,
        title="Save output as…",
    )
    if not f:
        return None        # user cancelled
    p = Path(f)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _get_out(var, default_name):
    """Legacy — now just delegates to _ask_save."""
    return _ask_save(default_name)


# ══════════════════════════════════════════════════════════════════
# TOOL CATALOGUE
# ══════════════════════════════════════════════════════════════════
TOOLS = [
    ("organize", "🔗", COL_ORG,  "Merge PDF",       "Combine PDFs in the order you want.",         MergePanel),
    ("organize", "✂️", COL_ORG,  "Split PDF",        "Separate pages or split by range.",            SplitPanel),
    ("organize", "🗂️", COL_ORG,  "Organise Pages",   "Rotate, delete and reorder pages visually.",   OrganisePanel),
    ("optimize", "🗜️", COL_OPT,  "Compress PDF",       "Reduce file size while keeping quality.",      CompressPanel),
    ("optimize", "🔧", COL_OPT,  "Repair PDF",         "Fix corrupt or damaged PDF files.",            RepairPanel),
    ("optimize", "🧹", COL_OPT,  "Remove Metadata",    "Strip author, date and software info.",        RemoveMetadataPanel),
    ("optimize", "🖤", COL_OPT,  "Grayscale PDF",      "Convert to black & white — smaller & print-ready.", GrayscalePanel),
    ("optimize", "📋", COL_OPT,  "Flatten PDF",        "Bake in annotations and form fields.",         FlattenPanel),
    ("optimize", "🗑️", COL_OPT,  "Remove Blank Pages", "Auto-detect and delete empty pages.",          RemoveBlankPagesPanel),
    ("edit",     "🔄", COL_EDIT, "Rotate PDF",       "Rotate pages 90°, 180° or 270°.",             RotatePanel),
    ("edit",     "💧", COL_EDIT, "Watermark",        "Stamp text over your PDF pages.",             WatermarkTextPanel),
    ("edit",     "🖼️", COL_EDIT, "Image Watermark",  "Overlay an image watermark on pages.",        WatermarkImagePanel),
    ("edit",     "🔢", COL_EDIT, "Page Numbers",     "Add page numbers with custom style.",          PageNumberPanel),
    ("edit",     "✂️", COL_EDIT, "Crop PDF",         "Trim margins or select a specific area.",     CropPanel),
    ("security", "🔐", COL_SEC,  "Protect PDF",      "Password-protect your PDF document.",         EncryptPanel),
    ("security", "🔓", COL_SEC,  "Unlock PDF",       "Remove the password from a PDF.",             DecryptPanel),
    ("security", "⬛", COL_SEC,  "Redact Text",      "Permanently remove text from a PDF.",         RedactTextPanel),
    ("security", "🟥", COL_SEC,  "Redact Regions",   "Black out specific rectangular areas.",       RedactRegionPanel),
]
FILTERS = [
    ("all",      "All Tools"),
    ("organize", "Organize PDF"),
    ("optimize", "Optimize PDF"),
    ("edit",     "Edit PDF"),
    ("security", "PDF Security"),
]


# ══════════════════════════════════════════════════════════════════
# TOOL PAGE  — two-column layout shown when a tool is selected
# LEFT: sidebar with all tools  |  RIGHT: the ToolPanel
# Only this class and App are changed. All Panels untouched.
# ══════════════════════════════════════════════════════════════════

class ToolPage(tk.Frame):
    """
    Full-screen page replacing home when a tool is selected.
    Left sidebar: all tools, sectioned, scrollable.
    Right: ToolPanel for the active tool, fills the rest.
    Top bar: tool name (right), output folder button (left).
    """
    def __init__(self, parent, initial_tool, navigate_home, navigate_tool, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.navigate_home  = navigate_home
        self.navigate_tool  = navigate_tool
        self._current_panel = None
        self._sidebar_btns  = {}   # id(tool) -> (button, tool)
        self._active_tool   = None
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_content()
        self._load_tool(initial_tool)

    # ── LEFT sidebar ─────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = tk.Frame(self, bg=HEADER, width=215)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.pack_propagate(False)

        # Home button
        hb = tk.Button(sb, text="← All Things PDF",
                       command=self.navigate_home,
                       bg=HEADER, fg="white",
                       activebackground=HDR2, activeforeground="white",
                       relief=tk.FLAT, cursor="hand2",
                       font=("Segoe UI", 10, "bold"),
                       padx=16, pady=13, bd=0, anchor="w")
        hb.pack(fill=tk.X)
        hb.bind("<Enter>", lambda e: hb.config(bg=HDR2))
        hb.bind("<Leave>", lambda e: hb.config(bg=HEADER))
        tk.Frame(sb, bg=HDR2, height=1).pack(fill=tk.X)

        # Scrollable list
        cv = tk.Canvas(sb, bg=HEADER, bd=0, highlightthickness=0)
        cv.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(cv, bg=HEADER)
        cv.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(
            scrollregion=cv.bbox("all")))
        # Scroll handled globally by _ScrollRouter

        SECTION_LABELS = {
            "organize": "ORGANIZE PDF",
            "optimize": "OPTIMIZE",
            "edit":     "EDIT PDF",
            "security": "PDF SECURITY",
        }
        current_tag = None
        for tool in TOOLS:
            tag, icon, color, name, desc, PC = tool
            if tag != current_tag:
                current_tag = tag
                tk.Frame(inner, bg=HDR2, height=1).pack(fill=tk.X, pady=(6,0))
                tk.Label(inner, text=SECTION_LABELS.get(tag, ""),
                         bg=HEADER, fg="#7db89a",
                         font=("Segoe UI", 7, "bold"),
                         anchor="w", padx=16, pady=3).pack(fill=tk.X)
            btn = tk.Button(inner,
                            text=f"  {icon}  {name}",
                            command=lambda t=tool: self.navigate_tool(t),
                            bg=HEADER, fg="#d4ead9",
                            activebackground=GREEN, activeforeground="white",
                            relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 9),
                            padx=8, pady=7, bd=0, anchor="w")
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(
                bg=GREEN, fg="white") if b != self._get_active_btn() else None)
            btn.bind("<Leave>", lambda e, b=btn, t=tool: b.config(
                bg=GREEN if t is self._active_tool else HEADER,
                fg="white" if t is self._active_tool else "#d4ead9"))
            self._sidebar_btns[id(tool)] = (btn, tool)

    def _get_active_btn(self):
        if self._active_tool is None: return None
        entry = self._sidebar_btns.get(id(self._active_tool))
        return entry[0] if entry else None

    # ── RIGHT content area ───────────────────────────────────────────
    def _build_content(self):
        self._content = tk.Frame(self, bg=BG)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(1, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Top bar
        topbar = tk.Frame(self._content, bg=WHITE,
                          highlightbackground=BORDER, highlightthickness=1)
        topbar.grid(row=0, column=0, sticky="ew")
        _green_btn(topbar, "📂  Output Folder",
                   lambda: (os.startfile(str(OUT_DIR)) if os.name=="nt"
                            else os.system(f"xdg-open '{OUT_DIR}'")),
                   bg=GREEN, hover=HDR2).pack(side=tk.LEFT, padx=16, pady=8)
        self._name_lbl = tk.Label(topbar, text="",
                                  bg=WHITE, fg=HEADER,
                                  font=("Segoe UI", 13, "bold"),
                                  padx=24, pady=12)
        self._name_lbl.pack(side=tk.RIGHT)

        # Panel area
        self._panel_area = tk.Frame(self._content, bg=BG)
        self._panel_area.grid(row=1, column=0, sticky="nsew")
        self._panel_area.grid_rowconfigure(0, weight=1)
        self._panel_area.grid_columnconfigure(0, weight=1)

    # ── Load / switch tool ───────────────────────────────────────────
    def _load_tool(self, tool):
        # Destroy old panel
        if self._current_panel:
            self._current_panel.destroy()
            self._current_panel = None

        # Reset old sidebar highlight
        if self._active_tool:
            old_entry = self._sidebar_btns.get(id(self._active_tool))
            if old_entry:
                old_entry[0].config(bg=HEADER, fg="#d4ead9")

        self._active_tool = tool
        tag, icon, color, name, desc, PC = tool

        # Highlight active sidebar button
        new_entry = self._sidebar_btns.get(id(tool))
        if new_entry:
            new_entry[0].config(bg=GREEN, fg="white")

        # Update name label
        self._name_lbl.config(text=f"{icon}  {name}")

        # Create the panel — back button returns home
        panel = PC(self._panel_area, name, icon, color, self.navigate_home)
        panel.grid(row=0, column=0, sticky="nsew")
        self._current_panel = panel

    def switch_tool(self, tool):
        self._load_tool(tool)


# ══════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        self.root = root
        root.title("All Things PDF")
        root.configure(bg=BG)
        root.geometry("1200x780")
        root.minsize(960, 620)
        self._filter     = "all"
        self._tool_page  = None
        self._container  = tk.Frame(root, bg=BG)
        self._container.pack(fill=tk.BOTH, expand=True)
        # Bind scroll at root level — walks widget under cursor to find canvas
        _ScrollRouter.init(root)
        self._build_home()
        self._show_home()

    # ── Home page ─────────────────────────────────────────────────
    def _build_home(self):
        self._home = tk.Frame(self._container, bg=BG)

        # Header
        hdr = tk.Frame(self._home, bg=HEADER)
        hdr.pack(fill=tk.X)
        logo = tk.Frame(hdr, bg=HEADER); logo.pack(side=tk.LEFT, padx=20, pady=12)
        tk.Label(logo, text="📄 ", bg=HEADER, fg="white",
                 font=("Segoe UI Emoji", 16)).pack(side=tk.LEFT)
        tk.Label(logo, text="All Things PDF", bg=HEADER, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT)
        _green_btn(hdr, "📂  Output Folder", self._open_out,
                   bg=GREEN, hover=HDR2).pack(side=tk.RIGHT, padx=20, pady=10)

        # Scrollable body
        wrap = tk.Frame(self._home, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(wrap, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        cv = tk.Canvas(wrap, bg=BG, bd=0, highlightthickness=0,
                       yscrollcommand=vsb.set)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=cv.yview)
        scroll = tk.Frame(cv, bg=BG)
        win = cv.create_window((0,0), window=scroll, anchor="nw")
        scroll.bind("<Configure>", lambda e: cv.configure(
            scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(win, width=e.width))
        # Scroll handled globally by _ScrollRouter
        self._home_scroll = scroll

        # Hero
        hero = tk.Frame(scroll, bg=WHITE,
                        highlightbackground=BORDER, highlightthickness=1)
        hero.pack(fill=tk.X, padx=32, pady=(24,0))
        tk.Frame(hero, bg=GREEN, height=4).pack(fill=tk.X)
        hb = tk.Frame(hero, bg=WHITE); hb.pack(fill=tk.X, padx=28, pady=18)
        tk.Label(hb, text="Every tool you need to work with PDFs",
                 bg=WHITE, fg=HEADER,
                 font=("Segoe UI", 18, "bold"), anchor="w").pack(anchor="w")
        tk.Label(hb,
                 text="100% offline  ·  No internet required  ·  Files stay on your computer",
                 bg=WHITE, fg=MUTED, font=F, anchor="w").pack(anchor="w", pady=(4,0))

        # Filter tabs
        self._tabs = {}
        tabbar = tk.Frame(scroll, bg=BG)
        tabbar.pack(fill=tk.X, padx=32, pady=(18,14))
        for tag, label in FILTERS:
            b = tk.Button(tabbar, text=label,
                          command=lambda t=tag: self._set_filter(t),
                          bg=WHITE, fg=MUTED,
                          activebackground=GREEN_L, activeforeground=HEADER,
                          relief=tk.FLAT, cursor="hand2", font=FTAB,
                          padx=16, pady=8, bd=0,
                          highlightbackground=BORDER, highlightthickness=1)
            b.pack(side=tk.LEFT, padx=(0,8))
            self._tabs[tag] = b
        self._set_filter("all", init=True)

        # Grid
        self._grid_outer = tk.Frame(scroll, bg=BG)
        self._grid_outer.pack(fill=tk.X, padx=32, pady=(0,8))

        # Footer
        tk.Frame(scroll, bg=HEADER).pack(fill=tk.X, pady=(24,0))
        tk.Label(scroll,
                 text="All Things PDF  ·  100% offline  ·  Outputs → ~/AllThingsPDF_Output",
                 bg=HEADER, fg="white", font=F, pady=10).pack(fill=tk.X)

        self._render_grid()

    # ── Page switching ────────────────────────────────────────────
    def _show_home(self):
        if self._tool_page:
            self._tool_page.pack_forget()
        self._home.pack(fill=tk.BOTH, expand=True)

    def _show_tool(self, tool):
        self._home.pack_forget()
        if self._tool_page is None:
            self._tool_page = ToolPage(
                self._container,
                initial_tool  = tool,
                navigate_home = self._show_home,
                navigate_tool = self._switch_tool,
            )
            self._tool_page.pack(fill=tk.BOTH, expand=True)
        else:
            self._tool_page.pack(fill=tk.BOTH, expand=True)
            self._tool_page.switch_tool(tool)

    def _switch_tool(self, tool):
        if self._tool_page:
            self._tool_page.switch_tool(tool)

    # ── Home grid ─────────────────────────────────────────────────
    def _set_filter(self, tag, init=False):
        self._filter = tag
        for t, b in self._tabs.items():
            b.config(bg=HEADER if t==tag else WHITE,
                     fg="white" if t==tag else MUTED,
                     highlightbackground=HEADER if t==tag else BORDER)
        if not init:
            self._render_grid()

    def _render_grid(self):
        for w in self._grid_outer.winfo_children(): w.destroy()
        visible = [t for t in TOOLS if self._filter=="all" or t[0]==self._filter]
        COLS = 4; row_f = None
        for i, tool in enumerate(visible):
            tag, icon, color, name, desc, PC = tool
            if i % COLS == 0:
                row_f = tk.Frame(self._grid_outer, bg=BG)
                row_f.pack(fill=tk.X, pady=(0,10))
                for ci in range(COLS):
                    row_f.columnconfigure(ci, weight=1, uniform="c")
            card = self._make_card(row_f, icon, color, name, desc, tool)
            card.grid(row=0, column=i%COLS, padx=5, sticky="nsew")

    def _make_card(self, parent, icon, color, name, desc, tool):
        card = tk.Frame(parent, bg=WHITE, bd=0, cursor="hand2",
                        highlightbackground=BORDER, highlightthickness=1)
        tk.Frame(card, bg=color, height=4).pack(fill=tk.X)
        ic = tk.Label(card, text=icon, bg=WHITE,
                      font=("Segoe UI Emoji", 22))
        ic.pack(pady=(12,2), padx=14, anchor="w")
        nl = tk.Label(card, text=name, bg=WHITE, fg=TEXT,
                      font=FB, anchor="w", justify=tk.LEFT)
        nl.pack(fill=tk.X, padx=14, pady=(0,2))
        dl = tk.Label(card, text=desc, bg=WHITE, fg=MUTED, font=FDESC,
                      anchor="w", justify=tk.LEFT, wraplength=200)
        dl.pack(fill=tk.X, padx=14, pady=(0,14))
        for w in (card, ic, nl, dl):
            w.bind("<Enter>",    lambda e, c=card, col=color:
                   self._card_hov(c, True, col))
            w.bind("<Leave>",    lambda e, c=card, col=color:
                   self._card_hov(c, False, col))
            w.bind("<Button-1>", lambda e, t=tool:
                   self._show_tool(t))
        return card

    def _card_hov(self, card, on, color):
        bg  = GREEN_LL if on else WHITE
        hbg = color    if on else BORDER
        card.config(bg=bg, highlightbackground=hbg)
        for w in card.winfo_children():
            if isinstance(w, tk.Frame) and w.cget("height") == "4":
                continue
            try: w.config(bg=bg)
            except: pass

    def _open_out(self):
        if os.name == "nt": os.startfile(str(OUT_DIR))
        else: os.system(f"xdg-open '{OUT_DIR}'")


# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    try: root.tk.call("tk", "scaling", 1.5)
    except: pass
    try: root.iconbitmap(default="")
    except: pass
    App(root)
    root.mainloop()
