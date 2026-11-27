"""
OCR engine for scanned PDFs and photos of statements.

Pages are rendered with pypdfium2 (no Poppler needed) and read with
Tesseract.  Before OCR each image is converted to greyscale, enlarged and
binarised, which noticeably improves the reading of amounts.
Tesseract must be installed on the PC (free: UB-Mannheim build for Windows);
its path is set on the Settings page.
"""
import os

from config.settings import load_settings


def _configure():
    import pytesseract
    path = load_settings().get("tesseract_path", "")
    if path and os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
    return pytesseract


def tesseract_available():
    try:
        pt = _configure()
        pt.get_tesseract_version()
        return True
    except Exception:
        return False


def preprocess(img):
    from PIL import ImageOps, ImageFilter
    g = ImageOps.grayscale(img)
    if g.width < 2000:
        scale = 2000.0 / g.width
        g = g.resize((int(g.width * scale), int(g.height * scale)))
    g = g.filter(ImageFilter.SHARPEN)
    g = g.point(lambda p: 255 if p > 170 else 0)
    return g


def ocr_image(img):
    pt = _configure()
    return pt.image_to_string(preprocess(img), config="--psm 6")


def render_pdf_pages(path, pages=None, scale=3.0):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    idx = range(len(pdf)) if pages is None else pages
    for i in idx:
        page = pdf[i]
        yield i, page.render(scale=scale).to_pil()


def ocr_pdf_page(path, page_index):
    for _, img in render_pdf_pages(path, [page_index]):
        return ocr_image(img)
    return ""


def ocr_image_file(path):
    from PIL import Image
    with Image.open(path) as im:
        return ocr_image(im.convert("RGB"))
