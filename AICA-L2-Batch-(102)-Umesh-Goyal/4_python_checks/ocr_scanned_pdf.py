r"""Scanned SCN (picture-only PDF) -> OCR text -> header fields.

Needs, once:  py -m pip install pymupdf pytesseract pillow   and the Tesseract program
(Windows default path below). OCR is never perfect on digits: always check the figures
against the original PDF, and keep the _ocr.txt in this folder: check_scn.py then uses it to confirm the figures of the AI Studio JSON.

Run:  py ocr_scanned_pdf.py ..\5_samples\sample_scn_scanned.pdf
"""
import io
import json
import os
import shutil
import sys

try:
    import pymupdf
except ImportError:                      # older PyMuPDF
    import fitz as pymupdf
import pytesseract
from PIL import Image

from scn_common import header_fields

WIN_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(WIN_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = WIN_TESSERACT
elif not shutil.which("tesseract"):
    sys.exit("Tesseract is not installed. Install it first (see README).")

LANG = "eng"            # use "eng+hin" for Hindi text, if the Hindi data file is installed


def main():
    interactive = len(sys.argv) < 2
    if interactive:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Choose the scanned PDF", filetypes=[("PDF", "*.pdf")])
    else:
        path = sys.argv[1]
    if not path:
        sys.exit("No file chosen.")

    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pages.append(pytesseract.image_to_string(img, lang=LANG, config="--psm 4"))  # psm 4 keeps table rows together
        print("Page %d/%d done" % (i, len(doc)))
    text = "\n".join(pages)

    base = os.path.splitext(path)[0]
    with open(base + "_ocr.txt", "w", encoding="utf-8") as f:
        f.write(text)
    result = header_fields(text, len(doc))
    with open(base + "_header.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\nSaved:", base + "_ocr.txt and _header.json")
    if interactive:
        input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
